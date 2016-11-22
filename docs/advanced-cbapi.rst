Job-based Live Response API Examples
====================================

Here's an example::

    import shutil
    from tempfile import NamedTemporaryFile
    import sqlite3
    from datetime import datetime
    from collections import defaultdict

    def chrome_history(lr_session):
        """Retrieve the 10 recent URLs from Chrome for every logged-in user's session"""

        running_processes = lr_session.list_processes()

        # get list of logged in users
        users = set([proc['username'].split('\\')[-1]
                     for proc in running_processes if proc['path'].find('explorer.exe') != -1])

        chrome_history_urls = defaultdict(list)

        for user in users:
            with NamedTemporaryFile(delete=False) as tf:
                try:
                    history_fp = lr_session.get_raw_file(
                        "c:\\users\\%s\\appdata\\local\\google\\chrome\\user data\\default\\history" % user)
                    shutil.copyfileobj(history_fp, tf.file)
                    tf.close()
                    db = sqlite3.connect(tf.name)
                    db.row_factory = sqlite3.Row
                    cur = db.cursor()
                    cur.execute(
                        "SELECT url, title, datetime(last_visit_time / 1000000 + (strftime('%s', '1601-01-01')), 'unixepoch') as last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 10")
                    urls = [dict(u) for u in cur.fetchall()]
                except:
                    pass
                else:
                    chrome_history_urls[user] = urls

        return chrome_history_urls

