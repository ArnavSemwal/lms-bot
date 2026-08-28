import sqlite3

DB_NAME = "lms_bot.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                course TEXT,
                title TEXT,
                due_date TEXT,
                link TEXT,
                status TEXT
            )
        ''')
        conn.commit()

def save_and_get_diff(course_name, assignments):
    new_or_updated = []
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        for item in assignments:
            assign_id = item['id']
            title = item['title']
            due_date = item['due_date']
            link = item['url']
            
            c.execute("SELECT status FROM assignments WHERE id = ?", (assign_id,))
            row = c.fetchone()
            
            if row is None:
                c.execute("INSERT INTO assignments (id, course, title, due_date, link, status) VALUES (?, ?, ?, ?, ?, ?)",
                          (assign_id, course_name, title, due_date, link, due_date))
                new_or_updated.append({"type": "NEW", "data": item, "course": course_name})
            elif row[0] != due_date:
                c.execute("UPDATE assignments SET status = ?, due_date = ? WHERE id = ?", (due_date, due_date, assign_id))
                new_or_updated.append({"type": "UPDATED", "data": item, "course": course_name})
        conn.commit()
    return new_or_updated
