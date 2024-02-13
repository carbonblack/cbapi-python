class GetFileJob(object):
    def __init__(self, file_name):
        self._file_name = file_name

    def run(self, session):
        return session.get_file(self._file_name)


def getjob():
    return GetFileJob("c:\\test.txt")
