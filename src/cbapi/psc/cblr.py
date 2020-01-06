import logging
import threading
from cbapi.six.moves.queue import Queue
from collections import defaultdict
from concurrent.futures import _base

from cbapi.errors import TimeoutError
from cbapi.live_response_api import CbLRManagerBase, CbLRSessionBase, poll_status


OS_LIVE_RESPONSE_ENUM = {
    "WINDOWS": 1,
    "LINUX": 2,
    "MAC": 4
}

log = logging.getLogger(__name__)


class LiveResponseSession(CbLRSessionBase):
    def __init__(self, cblr_manager, session_id, sensor_id, session_data=None):
        super(LiveResponseSession, self).__init__(cblr_manager, session_id, sensor_id, session_data=session_data)
        from cbapi.psc.defense.models import Device
        device_info = self._cb.select(Device, self.sensor_id)
        self.os_type = OS_LIVE_RESPONSE_ENUM.get(device_info.deviceType, None)


class WorkItem(object):
    def __init__(self, fn, sensor_id):
        from cbapi.psc.defense.models import Device
        self.fn = fn
        if isinstance(sensor_id, Device):
            self.sensor_id = sensor_id.deviceId
        else:
            self.sensor_id = int(sensor_id)

        self.future = _base.Future()


class CompletionNotification(object):
    def __init__(self, sensor_id):
        self.sensor_id = sensor_id


class WorkerStatus(object):
    def __init__(self, sensor_id, status="ready", exception=None):
        self.sensor_id = sensor_id
        self.status = status
        self.exception = exception


class JobWorker(threading.Thread):
    def __init__(self, cb, sensor_id, result_queue):
        super(JobWorker, self).__init__()
        self.cb = cb
        self.sensor_id = sensor_id
        self.job_queue = Queue()
        self.lr_session = None
        self.result_queue = result_queue

    def run(self):
        try:
            self.lr_session = self.cb.live_response.request_session(self.sensor_id)
            self.result_queue.put(WorkerStatus(self.sensor_id, status="ready"))

            while True:
                work_item = self.job_queue.get(block=True)
                if not work_item:
                    self.job_queue.task_done()
                    return

                self.run_job(work_item)
                self.result_queue.put(CompletionNotification(self.sensor_id))
                self.job_queue.task_done()
        except Exception as e:
            self.result_queue.put(WorkerStatus(self.sensor_id, status="error", exception=e))
        finally:
            if self.lr_session:
                self.lr_session.close()
            self.result_queue.put(WorkerStatus(self.sensor_id, status="exiting"))

    def run_job(self, work_item):
        try:
            work_item.future.set_result(work_item.fn(self.lr_session))
        except Exception as e:
            work_item.future.set_exception(e)


class LiveResponseSessionManager(CbLRManagerBase):
    cblr_base = "/integrationServices/v3/cblr"
    cblr_session_cls = LiveResponseSession

    def submit_job(self, job, sensor):
        if self._job_scheduler is None:
            # spawn the scheduler thread
            self._job_scheduler = LiveResponseJobScheduler(self._cb)
            self._job_scheduler.start()

        work_item = WorkItem(job, sensor)
        self._job_scheduler.submit_job(work_item)
        return work_item.future

    def _get_or_create_session(self, sensor_id):
        session_id = self._create_session(sensor_id)

        try:
            res = poll_status(self._cb, "{cblr_base}/session/{0}".format(session_id, cblr_base=self.cblr_base),
                              desired_status="ACTIVE", delay=1, timeout=360)
        except Exception:
            # "close" the session, otherwise it will stay in a pending state
            self._close_session(session_id)

            # the Cb server will return a 404 if we don't establish a session in time, so convert this to a "timeout"
            raise TimeoutError(uri="{cblr_base}/session/{0}".format(session_id, cblr_base=self.cblr_base),
                               message="Could not establish session with sensor {0}".format(sensor_id),
                               error_code=404)
        else:
            return session_id, res

    def _close_session(self, session_id):
        try:
            self._cb.put_object("{cblr_base}/session".format(session_id, cblr_base=self.cblr_base),
                                {"session_id": session_id, "status": "CLOSE"})
        except Exception:
            pass

    def _create_session(self, sensor_id):
        response = self._cb.post_object("{cblr_base}/session/{0}".format(sensor_id, cblr_base=self.cblr_base),
                                        {"sensor_id": sensor_id}).json()
        session_id = response["id"]
        return session_id


class LiveResponseJobScheduler(threading.Thread):
    daemon = True

    def __init__(self, cb, max_workers=10):
        super(LiveResponseJobScheduler, self).__init__()
        self._cb = cb
        self._job_workers = {}
        self._idle_workers = set()
        self._unscheduled_jobs = defaultdict(list)
        self._max_workers = max_workers
        self.schedule_queue = Queue()

    def run(self):
        log.debug("Starting Live Response Job Scheduler")

        while True:
            log.debug("Waiting for item on Scheduler Queue")
            item = self.schedule_queue.get(block=True)
            log.debug("Got item: {0}".format(item))
            if isinstance(item, WorkItem):
                # new WorkItem available
                self._unscheduled_jobs[item.sensor_id].append(item)
            elif isinstance(item, CompletionNotification):
                # job completed
                self._idle_workers.add(item.sensor_id)
            elif isinstance(item, WorkerStatus):
                if item.status == "error":
                    log.error("Error encountered by JobWorker[{0}]: {1}".format(item.sensor_id,
                                                                                item.exception))
                elif item.status == "exiting":
                    log.debug("JobWorker[{0}] has exited, waiting...".format(item.sensor_id))
                    self._job_workers[item.sensor_id].join()
                    log.debug("JobWorker[{0}] deleted".format(item.sensor_id))
                    del self._job_workers[item.sensor_id]
                    try:
                        self._idle_workers.remove(item.sensor_id)
                    except KeyError:
                        pass
                elif item.status == "ready":
                    log.debug("JobWorker[{0}] now ready to accept jobs, session established".format(item.sensor_id))
                    self._idle_workers.add(item.sensor_id)
                else:
                    log.debug("Unknown status from JobWorker[{0}]: {1}".format(item.sensor_id, item.status))
            else:
                log.debug("Received unknown item on the scheduler Queue, exiting")
                # exiting the scheduler if we get None
                # TODO: wait for all worker threads to exit
                return

            self._schedule_jobs()

    def _schedule_jobs(self):
        log.debug("Entering scheduler")

        # First, see if there are new jobs to schedule on idle workers.
        self._schedule_existing_workers()

        # If we have jobs scheduled to run on sensors with no current associated worker, let's spawn new ones.
        if set(self._unscheduled_jobs.keys()) - self._idle_workers:
            self._cleanup_idle_workers()
            self._spawn_new_workers()
            self._schedule_existing_workers()

    def _cleanup_idle_workers(self, max=None):
        if not max:
            max = self._max_workers

        for sensor in list(self._idle_workers)[:max]:
            log.debug("asking worker for sensor id {0} to exit".format(sensor))
            self._job_workers[sensor].job_queue.put(None)

    def _schedule_existing_workers(self):
        log.debug("There are idle workers for sensor ids {0}".format(self._idle_workers))

        intersection = self._idle_workers.intersection(set(self._unscheduled_jobs.keys()))

        log.debug("{0} jobs ready to execute in existing execution slots".format(len(intersection)))

        for sensor in intersection:
            item = self._unscheduled_jobs[sensor].pop(0)
            self._job_workers[sensor].job_queue.put(item)
            self._idle_workers.remove(item.sensor_id)

        self._cleanup_unscheduled_jobs()

    def _cleanup_unscheduled_jobs(self):
        marked_for_deletion = []
        for k in self._unscheduled_jobs.keys():
            if len(self._unscheduled_jobs[k]) == 0:
                marked_for_deletion.append(k)

        for k in marked_for_deletion:
            del self._unscheduled_jobs[k]

    def submit_job(self, work_item):
        self.schedule_queue.put(work_item)

    def _spawn_new_workers(self):
        from cbapi.psc.defense.models import Device
        if len(self._job_workers) >= self._max_workers:
            return

        schedule_max = self._max_workers - len(self._job_workers)
        '''
        sensors = [s for s in self._cb.select(Device) if s.deviceId in self._unscheduled_jobs
                    and s.deviceId not in self._job_workers
                    and "AVAILABLE" in s.sensorStates]
        '''
        log.debug("spawning new workers to handle unscheduled jobs: {0}".format(self._unscheduled_jobs))
        sensors = [s for s in self._cb.select(Device) if s.deviceId in self._unscheduled_jobs
                   and s.deviceId not in self._job_workers]
        sensors_to_schedule = sensors[:schedule_max]
        log.debug("Spawning new workers to handle these sensors: {0}".format(sensors_to_schedule))
        for sensor in sensors_to_schedule:
            log.debug("Spawning new JobWorker for sensor id {0}".format(sensor.deviceId))
            self._job_workers[sensor.deviceId] = JobWorker(self._cb, sensor.deviceId, self.schedule_queue)
            self._job_workers[sensor.deviceId].start()
