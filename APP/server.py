from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import bcrypt
from datetime import datetime
import os
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# Path definition pointing to your news page file context
NEWS_FILE_PATH = os.path.join(os.getcwd(), "news2.html")


# DATABASE CONNECTION

conn = psycopg2.connect(
    host="localhost",
    database="urbandrive_db",
    user="postgres",
    password="",
    port="5432"
)

cursor = conn.cursor()

# Helper utility to read structural anchors out of news2.html file lines safely
def parse_scrapers_from_file():
    if not os.path.exists(NEWS_FILE_PATH):
        # Create a basic sample file if news2.html doesn't exist yet to prevent crashes
        with open(NEWS_FILE_PATH, "w", encoding="utf-8") as f:
            f.write('\n<a href="https://nation.co.ke">Nation Media</a>\n<a href="https://standardmedia.co.ke">The Standard</a>\n')
    
    with open(NEWS_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    links = soup.find_all('a')
    
    scrapers = []
    for idx, link in enumerate(links):
        href = link.get('href', '')
        # Only parse actual web addresses matching external data targets
        if href.startswith('http://') or href.startswith('https://'):
            scrapers.append({
                "id": idx + 1,
                "name": link.text.strip() if link.text.strip() else href,
                "url": href
            })
    return scrapers

# =========================
# SIGNUP
# =========================
@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()

        full_name = data.get('full_name')
        username = data.get('username')
        email = data.get('email')
        phone_number = data.get('phone_number')
        country = data.get('country')
        password = data.get('password')
        role = "User"

        cursor.execute("""
            SELECT user_id FROM users
            WHERE email = %s OR username = %s
        """, (email, username))

        if cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "User already exists"
            }), 400

        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        cursor.execute("""
            INSERT INTO users (
                full_name,
                username,
                email,
                phone_number,
                country,
                password_hash,
                role
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            full_name,
            username,
            email,
            phone_number,
            country,
            hashed_password,
            role
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Account created successfully"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        email = data.get('email')
        password = data.get('password')

        cursor.execute("""
            SELECT user_id, email, password_hash, role
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        user_id, db_email, db_password, role = user

        if bcrypt.checkpw(password.encode('utf-8'), db_password.encode('utf-8')):
            return jsonify({
                "success": True,
                "user_id": user_id,
                "email": db_email,
                "role": role.lower()
            })

        return jsonify({
            "success": False,
            "message": "Invalid password"
        }), 401

    except psycopg2.Error as db_error:
        conn.rollback()
        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(db_error)
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Server error",
            "error": str(e)
        }), 500


# =========================
# SAVE REPORT
# =========================
@app.route('/save-report', methods=['POST'])
def save_report():
    try:
        data = request.get_json()
        details = data.get('details', [])

        cursor.execute("""
            INSERT INTO reports (
                user_id,
                report_title,
                region,
                building_type,
                units,
                avg_unit_size_sqm,
                land_size_acres,
                soil_condition,
                commencement_lead_time_months,
                high_end_finishes,
                advanced_security,
                gps_latitude,
                gps_longitude,
                total_investment,
                projected_monthly_revenue,
                annual_roi,
                verdict
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING report_id
        """, (
            data.get('user_id'),
            data.get('report_title'),
            data.get('region'),
            data.get('building_type'),
            data.get('units'),
            data.get('avg_unit_size_sqm'),
            data.get('land_size_acres'),
            data.get('soil_condition'),
            data.get('commencement_lead_time_months'),
            data.get('high_end_finishes'),
            data.get('advanced_security'),
            data.get('gps_latitude'),
            data.get('gps_longitude'),
            data.get('total_investment'),
            data.get('projected_monthly_revenue'),
            data.get('annual_roi'),
            data.get('verdict')
        ))

        report_id = cursor.fetchone()[0]

        for item in details:
            cursor.execute("""
                INSERT INTO report_details (
                    report_id,
                    category,
                    item_name,
                    amount_kes
                )
                VALUES (%s,%s,%s,%s)
            """, (
                report_id,
                item.get('category'),
                item.get('item_name'),
                item.get('amount_kes')
            ))

        conn.commit()

        return jsonify({
            "success": True,
            "report_id": report_id
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================
# GET REPORTS
# =========================
@app.route('/get-reports/<int:user_id>', methods=['GET'])
def get_reports(user_id):
    try:
        cursor.execute("""
            SELECT report_id, report_title, region, total_investment,
                   projected_monthly_revenue, annual_roi, verdict
            FROM reports
            WHERE user_id = %s
            ORDER BY report_id DESC
        """, (user_id,))

        rows = cursor.fetchall()

        reports = [
            {
                "report_id": r[0],
                "report_title": r[1],
                "region": r[2],
                "total_investment": r[3],
                "projected_monthly_revenue": r[4],
                "annual_roi": r[5],
                "verdict": r[6]
            }
            for r in rows
        ]

        return jsonify({
            "success": True,
            "reports": reports
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================
# HEALTH CHECK
# =========================
@app.route('/')
def home():
    return jsonify({
        "status": "URBANDRIVE API running"
    })


# =========================
# ADMIN: FETCH ALL USER REPORTS
# =========================
@app.route('/admin/all-reports', methods=['GET'])
def get_admin_all_reports():
    try:
        cursor.execute("""
            SELECT 
                r.report_id, 
                r.report_title, 
                u.email, 
                r.region,
                r.created_at
            FROM reports r
            JOIN users u ON r.user_id = u.user_id
            ORDER BY r.report_id DESC
        """)

        rows = cursor.fetchall()

        admin_reports = [
            {
                "id": r[0],
                "title": r[1] if r[1] else f"{r[3]} Housing Analysis",
                "user": r[2],
                "focus": r[3],
                "date": r[4].strftime("%b %d, %Y") if r[4] else "N/A"
            }
            for r in rows
        ]

        return jsonify(admin_reports), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch administrative data",
            "error": str(e)
        }), 500


# =========================
# ADMIN: FETCH ALL USERS
# =========================
@app.route('/admin/users', methods=['GET'])
def admin_get_users():
    try:
        cursor.execute("""
            SELECT user_id, full_name, username, email, role, created_at 
            FROM users 
            ORDER BY user_id DESC
        """)
        rows = cursor.fetchall()
        
        users_list = [
            {
                "id": r[0],
                "fullname": r[1],
                "username": r[2],
                "email": r[3],
                "role": r[4].lower() if r[4] else "user",
                "joined": r[5].strftime("%b %Y") if r[5] else "N/A"
            }
            for r in rows
        ]
        return jsonify(users_list), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =========================
# ADMIN: TOGGLE USER ROLE
# =========================
@app.route('/admin/users/<int:user_id>/toggle-role', methods=['POST'])
def admin_toggle_role(user_id):
    try:
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        res = cursor.fetchone()
        if not res:
            return jsonify({"success": False, "message": "User not found"}), 404
            
        current_role = res[0].lower() if res[0] else "user"
        new_role = "Admin" if current_role == "user" else "User"
        
        cursor.execute("UPDATE users SET role = %s WHERE user_id = %s", (new_role, user_id))
        conn.commit()
        return jsonify({"success": True, "message": f"User role modified to {new_role}", "new_role": new_role.lower()}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# =========================
# ADMIN: DELETE USER
# =========================
@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "User not found"}), 404
            
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({"success": True, "message": "User erased successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# =========================
# ADMIN: CREATE USER
# =========================
@app.route('/admin/users/create', methods=['POST'])
def admin_create_user():
    try:
        data = request.get_json()
        full_name = data.get('full_name')
        username = data.get('username')
        email = data.get('email')
        role = data.get('role', 'User').capitalize()
        password = "DefaultUrbandrive123!" 

        cursor.execute("SELECT user_id FROM users WHERE email = %s OR username = %s", (email, username))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "User matching email or username already exists"}), 400

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("""
            INSERT INTO users (full_name, username, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id, created_at
        """, (full_name, username, email, hashed_password, role))
        
        new_id, created_at = cursor.fetchone()
        conn.commit()
        
        return jsonify({
            "success": True,
            "message": "User added dynamically into system database structures",
            "user": {
                "id": new_id,
                "fullname": full_name,
                "username": username,
                "email": email,
                "role": role.lower(),
                "joined": created_at.strftime("%b %Y") if created_at else datetime.now().strftime("%b %Y")
            }
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# =======================================================
# NEW MODULE: FILE SCRAPER ENGINE INTERFACES (news2.html)
# =======================================================
@app.route('/admin/scrapers', methods=['GET'])
def get_file_scrapers():
    try:
        scrapers = parse_scrapers_from_file()
        return jsonify({"success": True, "scrapers": scrapers}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/admin/scrapers/save', methods=['POST'])
def save_file_scrapers():
    try:
        data = request.get_json()
        scrapers_list = data.get('scrapers', [])
        
        # Build raw clean HTML tags containing structural target definitions
        html_output = "\n"
        for item in scrapers_list:
            name = item.get('name', '').strip()
            url = item.get('url', '').strip()
            if url:
                html_output += f'<a href="{url}">{name if name else url}</a>\n'
        html_output += ""
        
        # Rewrite data files block structure configurations cleanly
        with open(NEWS_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(html_output)
            
        return jsonify({"success": True, "message": "news2.html file updated successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# =========================
# RUN SERVER
# =========================
if __name__ == '__main__':
    app.run(debug=True)