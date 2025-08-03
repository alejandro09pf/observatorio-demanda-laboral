import psycopg2
from .settings import DB_PARAMS

class JobPipeline:
    def process_item(self, item, spider):
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO raw_jobs (portal, url, title, company, ...) VALUES (%s, %s, %s, %s, ...)",
            (item["portal"], item["url"], item["title"], item["company"], ...)
        )
        conn.commit()
        cur.close()
        conn.close()
        return item
