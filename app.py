import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = "cospace_hub_secret_key_pas_2024"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------

def get_db():
    """Open a new database connection for the current request context."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row          # access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and seed default data if the DB is fresh."""
    conn = get_db()
    cur = conn.cursor()

    # --- DDL ---
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id_user   INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            role      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ruangan (
            id_ruangan    INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_ruangan  TEXT UNIQUE NOT NULL,
            tipe_ruangan  TEXT NOT NULL,
            harga_per_jam REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS booking (
            id_booking    INTEGER PRIMARY KEY AUTOINCREMENT,
            id_user       INTEGER,
            id_ruangan    INTEGER,
            tanggal_sewa  TEXT NOT NULL,
            durasi_jam    INTEGER NOT NULL,
            total_bayar   REAL,
            status_booking TEXT DEFAULT 'Booked',
            FOREIGN KEY(id_user)    REFERENCES users(id_user),
            FOREIGN KEY(id_ruangan) REFERENCES ruangan(id_ruangan)
        );
    """)

    # --- Seed: default accounts (only if users table is empty) ---
    existing = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        cur.executemany(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            [
                ("superadmin",  "super123",  "super_admin"),
                ("resepsionis", "resep123",  "admin_resepsionis"),
                ("customer1",   "cust123",   "user_customer"),
            ]
        )

    # --- Seed: sample rooms (only if ruangan table is empty) ---
    existing_rooms = cur.execute("SELECT COUNT(*) FROM ruangan").fetchone()[0]
    if existing_rooms == 0:
        cur.executemany(
            "INSERT INTO ruangan (nama_ruangan, tipe_ruangan, harga_per_jam) VALUES (?, ?, ?)",
            [
                ("Hot Desk A",       "Hot Desk",       25000),
                ("Hot Desk B",       "Hot Desk",       25000),
                ("Meeting Room 1",   "Meeting Room",   75000),
                ("Meeting Room 2",   "Meeting Room",   75000),
                ("Private Office 1", "Private Office", 150000),
                ("Private Office 2", "Private Office", 150000),
            ]
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auth Decorators
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("role") not in roles:
                flash("Akses ditolak. Anda tidak memiliki izin.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ---------------------------------------------------------------------------
# Routes — Auth
# ---------------------------------------------------------------------------

@app.route("/")
def landing():
    """Landing page - accessible to all (unauthenticated users)"""
    if "user_id" in session:
        return _redirect_by_role(session["role"])
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page - redirect to dashboard if already logged in"""
    if "user_id" in session:
        return _redirect_by_role(session["role"])

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"]  = user["id_user"]
            session["username"] = user["username"]
            session["role"]     = user["role"]
            return _redirect_by_role(user["role"])
        else:
            error = "Username atau password salah. Silakan coba lagi."

    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return _redirect_by_role(session["role"])

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # --- Validation ---
        if not username or not password:
            error = "Username dan password tidak boleh kosong."
        elif len(username) < 3:
            error = "Username minimal 3 karakter."
        elif len(password) < 6:
            error = "Password minimal 6 karakter."
        else:
            conn = get_db()
            # Check if username already exists
            existing_user = conn.execute(
                "SELECT id_user FROM users WHERE username = ?", (username,)
            ).fetchone()

            if existing_user:
                error = "Username sudah terdaftar, bro!"
                conn.close()
            else:
                # Register as user_customer (hardcoded)
                conn.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, password, "user_customer")
                )
                conn.commit()
                conn.close()
                
                flash("Pendaftaran berhasil! Silakan login dengan akun Anda.", "success")
                return redirect(url_for("login"))

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah berhasil logout.", "success")
    return redirect(url_for("login"))


def _redirect_by_role(role):
    if role == "super_admin":
        return redirect(url_for("dashboard_super"))
    elif role == "admin_resepsionis":
        return redirect(url_for("dashboard_admin"))
    elif role == "user_customer":
        return redirect(url_for("dashboard_user"))
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Routes — Super Admin
# ---------------------------------------------------------------------------

@app.route("/dashboard/super")
@login_required
@role_required("super_admin")
def dashboard_super():
    conn = get_db()

    # Total revenue: only 'Done' bookings
    total_omset = conn.execute(
        "SELECT COALESCE(SUM(total_bayar), 0) FROM booking WHERE status_booking = 'Done'"
    ).fetchone()[0]

    # Counts per status
    stats = {}
    for row in conn.execute(
        "SELECT status_booking, COUNT(*) as cnt FROM booking GROUP BY status_booking"
    ).fetchall():
        stats[row["status_booking"]] = row["cnt"]

    total_booking  = stats.get("Booked", 0) + stats.get("Done", 0) + stats.get("Cancelled", 0)
    total_done     = stats.get("Done", 0)
    total_booked   = stats.get("Booked", 0)
    total_cancelled = stats.get("Cancelled", 0)

    # Revenue breakdown per room type
    revenue_by_type = conn.execute("""
        SELECT r.tipe_ruangan,
               COALESCE(SUM(b.total_bayar), 0) AS omset,
               COUNT(b.id_booking) AS jumlah
        FROM ruangan r
        LEFT JOIN booking b ON r.id_ruangan = b.id_ruangan AND b.status_booking = 'Done'
        GROUP BY r.tipe_ruangan
    """).fetchall()

    # Recent 'Done' transactions
    recent_done = conn.execute("""
        SELECT b.id_booking, u.username, r.nama_ruangan,
               b.tanggal_sewa, b.durasi_jam, b.total_bayar
        FROM booking b
        JOIN users u   ON b.id_user    = u.id_user
        JOIN ruangan r ON b.id_ruangan = r.id_ruangan
        WHERE b.status_booking = 'Done'
        ORDER BY b.id_booking DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard_super.html",
        total_omset=total_omset,
        total_booking=total_booking,
        total_done=total_done,
        total_booked=total_booked,
        total_cancelled=total_cancelled,
        revenue_by_type=revenue_by_type,
        recent_done=recent_done,
    )


# ---------------------------------------------------------------------------
# Routes — Admin Resepsionis
# ---------------------------------------------------------------------------

@app.route("/dashboard/admin")
@login_required
@role_required("admin_resepsionis")
def dashboard_admin():
    filter_status = request.args.get("status", "all")
    conn = get_db()

    query = """
        SELECT b.id_booking, u.username, r.nama_ruangan, r.tipe_ruangan,
               b.tanggal_sewa, b.durasi_jam, b.total_bayar, b.status_booking
        FROM booking b
        JOIN users   u ON b.id_user    = u.id_user
        JOIN ruangan r ON b.id_ruangan = r.id_ruangan
    """
    if filter_status != "all":
        rows = conn.execute(query + " WHERE b.status_booking = ? ORDER BY b.id_booking DESC", (filter_status,)).fetchall()
    else:
        rows = conn.execute(query + " ORDER BY b.id_booking DESC").fetchall()

    # Summary counts for the filter pills
    counts = {}
    for row in conn.execute("SELECT status_booking, COUNT(*) c FROM booking GROUP BY status_booking").fetchall():
        counts[row["status_booking"]] = row["c"]

    conn.close()
    return render_template("dashboard_admin.html", bookings=rows, filter_status=filter_status, counts=counts)


@app.route("/dashboard/admin/update/<int:id_booking>", methods=["POST"])
@login_required
@role_required("admin_resepsionis")
def update_status(id_booking):
    new_status = request.form.get("new_status")
    allowed = ("Done", "Cancelled")

    if new_status not in allowed:
        flash("Status tidak valid.", "danger")
        return redirect(url_for("dashboard_admin"))

    conn = get_db()
    booking = conn.execute(
        "SELECT status_booking FROM booking WHERE id_booking = ?", (id_booking,)
    ).fetchone()

    if not booking:
        flash("Data booking tidak ditemukan.", "danger")
        conn.close()
        return redirect(url_for("dashboard_admin"))

    if booking["status_booking"] != "Booked":
        flash("Hanya booking berstatus 'Booked' yang dapat diubah.", "warning")
        conn.close()
        return redirect(url_for("dashboard_admin"))

    conn.execute(
        "UPDATE booking SET status_booking = ? WHERE id_booking = ?",
        (new_status, id_booking)
    )
    conn.commit()
    conn.close()

    status_label = "Selesai ✓" if new_status == "Done" else "Dibatalkan"
    flash(f"Booking #{id_booking} berhasil ditandai sebagai '{status_label}'.", "success")
    return redirect(url_for("dashboard_admin"))


# ---------------------------------------------------------------------------
# Routes — User Customer
# ---------------------------------------------------------------------------

@app.route("/dashboard/user", methods=["GET", "POST"])
@login_required
@role_required("user_customer")
def dashboard_user():
    conn = get_db()
    ruangan_list = conn.execute("SELECT * FROM ruangan ORDER BY tipe_ruangan, nama_ruangan").fetchall()

    if request.method == "POST":
        id_ruangan  = request.form.get("id_ruangan")
        tanggal     = request.form.get("tanggal_sewa")
        durasi      = request.form.get("durasi_jam")

        # --- Validation ---
        errors = []
        if not id_ruangan:
            errors.append("Pilih ruangan terlebih dahulu.")
        if not tanggal:
            errors.append("Tanggal sewa harus diisi.")
        if not durasi or not durasi.isdigit() or int(durasi) < 1:
            errors.append("Durasi jam harus berupa angka positif (minimal 1 jam).")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            durasi = int(durasi)
            room = conn.execute(
                "SELECT harga_per_jam FROM ruangan WHERE id_ruangan = ?", (id_ruangan,)
            ).fetchone()

            if not room:
                flash("Ruangan tidak ditemukan.", "danger")
            else:
                # --- Backend Trigger: auto-calculate total_bayar ---
                total_bayar = room["harga_per_jam"] * durasi

                conn.execute(
                    """INSERT INTO booking (id_user, id_ruangan, tanggal_sewa, durasi_jam, total_bayar, status_booking)
                       VALUES (?, ?, ?, ?, ?, 'Booked')""",
                    (session["user_id"], id_ruangan, tanggal, durasi, total_bayar)
                )
                conn.commit()
                flash(
                    f"Booking berhasil! Total yang harus dibayar: Rp {total_bayar:,.0f}. "
                    "Silakan datang ke lokasi untuk konfirmasi.",
                    "success"
                )

    # Riwayat booking milik customer yang sedang login
    riwayat = conn.execute("""
        SELECT b.id_booking, r.nama_ruangan, r.tipe_ruangan,
               b.tanggal_sewa, b.durasi_jam, b.total_bayar, b.status_booking
        FROM booking b
        JOIN ruangan r ON b.id_ruangan = r.id_ruangan
        WHERE b.id_user = ?
        ORDER BY b.id_booking DESC
    """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("dashboard_user.html", ruangan_list=ruangan_list, riwayat=riwayat)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
init_db()


if __name__ == "__main__":
    app.run(debug=True)
