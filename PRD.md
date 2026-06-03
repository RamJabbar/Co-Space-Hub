# Product Requirement Document (PRD)
## Project Name: Co-Space Hub (Web-Based Coworking Space Booking System)

---

## 1. Project Overview & Objective
Aplikasi ini adalah sistem manajemen dan pemesanan tempat kerja (*coworking space*) berbasis web. Aplikasi ini dibuat menggunakan **Python (Flask)** dan **SQLite** untuk memenuhi kriteria Project Akhir Semester (PAS) kelas X SIJA, sekaligus sebagai portofolio ril yang fungsional (*usable*).

### Developer Guidelines (CRITICAL)
- **Role**: Anda adalah Senior Full-Stack Python Developer.
- **Strict Rule**: Ikuti spesifikasi teknis dan desain di bawah ini secara mutlak. Jangan menulis kode di luar cakupan atau mengubah skema database tanpa instruksi.
- **Goal**: Hasilkan kode yang modular, bersih (*clean code*), aman dari SQL injection, dan langsung siap pakai.

---

## 2. Technical Stack
- **Backend Framework**: Python Flask
- **Database**: SQLite3 (Native/Standard Library Python)
- **Frontend Framework**: Tailwind CSS (via CDN)
- **Session Management**: Flask Session (untuk auth state)

---

## 3. UI/UX Style Guide (Warm, Calm & Clean)
Aplikasi harus memiliki tampilan yang bersih, minimalis, modern, dengan nuansa hangat (*warm cozy cafe vibes*). 

### Color Palette (Wajib Digunakan di Tailwind)
- **Primary / Background Utama**: Krem Lembut (`bg-[#FDFBF7]`)
- **Card / Surface**: Putih Bersih (`bg-white`)
- **Text Utama / Headers**: Coklat Gelap/Tua (`text-[#3E2723]`)
- **Accent / Buttons / Highlights**: Coklat Hangat/Muted (`bg-[#8D6E63]` & hover:`bg-[#6D4C41]`)
- **Secondary Text**: Muted Brown/Gray (`text-[#795548]`)
- **Borders / Dividers**: Krem Muted (`border-[#EFEBE9]`)

---

## 4. User Leveling & Access Control
Sistem **WAJIB** memisahkan hak akses login menjadi 3 tingkat berdasarkan kolom `role` di database:

1. **Super Admin (`super_admin`)**
   - Halaman: `/superadmin`
   - Fungsi: Membaca laporan analitik bisnis global (Total omset pendapatan uang masuk dari transaksi yang berstatus 'Done').
2. **Admin Resepsionis (`admin_resepsionis`)**
   - Halaman: `/resepsionis`
   - Fungsi: Melihat semua antrean *booking*, melakukan update status pemakaian tempat (`Booked` -> `Done` / `Cancelled`).
3. **User Customer (`user_customer`)**
   - Halaman: `/customer`
   - Fungsi: Melakukan order sewa baru (Create data), melihat riwayat *booking* miliknya sendiri (Read data).

---

## 5. Skema Database (SQLite)
Struktur tabel harus relasional dan wajib diinisialisasi secara otomatis jika file `database.db` belum ada.

```sql
-- 1. Tabel Users
CREATE TABLE IF NOT EXISTS users (
    id_user INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL -- 'super_admin', 'admin_resepsionis', 'user_customer'
);

-- 2. Tabel Ruangan
CREATE TABLE IF NOT EXISTS ruangan (
    id_ruangan INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_ruangan TEXT UNIQUE NOT NULL,
    tipe_ruangan TEXT NOT NULL, -- 'Hot Desk', 'Meeting Room', 'Private Office'
    harga_per_jam REAL NOT NULL
);

-- 3. Tabel Booking (Data Utama & Transaksi)
CREATE TABLE IF NOT EXISTS booking (
    id_booking INTEGER PRIMARY KEY AUTOINCREMENT,
    id_user INTEGER,
    id_ruangan INTEGER,
    tanggal_sewa TEXT NOT NULL,
    durasi_jam INTEGER NOT NULL,
    total_bayar REAL, -- Dihitung otomatis oleh Backend Trigger
    status_booking TEXT DEFAULT 'Booked', -- 'Booked', 'Done', 'Cancelled'
    FOREIGN KEY(id_user) REFERENCES users(id_user),
    FOREIGN KEY(id_ruangan) REFERENCES ruangan(id_ruangan)
);  

## 6. Workflow & State Management (Alur Kerja Sistem)
Aplikasi ini berjalan berdasarkan perubahan status (*state changes*) dari sebuah pesanan sewa ruangan. Berikut adalah alur kerja riil yang harus diimplementasikan oleh sistem:

1. **Fase 1: Pembuatan Booking (User Customer)**
   - `user_customer` masuk ke dashboard, memilih ruangan, tanggal, dan durasi jam, lalu klik "Book" (CRUD Create).
   - Sistem memicu *Backend Trigger* untuk menghitung `total_bayar`.
   - Data tersimpan di database dengan `status_booking` default: `'Booked'`.
   - Di halaman Customer, pesanan ini masuk ke tabel riwayat dengan keterangan "Menunggu Konfirmasi/Selesai".

2. **Fase 2: Validasi & Eksekusi Lapangan (Admin Resepsionis)**
   - Ketika Customer datang ke lokasi *coworking space*, `admin_resepsionis` akan melihat data booking tersebut di dashboard mereka (CRUD Read).
   - Setelah Customer menyelesaikan pemakaian ruangan atau membayar di tempat, Admin mengklik tombol **"Selesai"** di web.
   - Aksi ini melakukan CRUD Update pada `status_booking` dari `'Booked'` berubah menjadi `'Done'`.

3. **Fase 3: Rekapitalisasi Otomatis (Super Admin)**
   - Begitu status berubah menjadi `'Done'`, nominal `total_bayar` dari transaksi tersebut secara otomatis akan masuk ke dalam hitungan fungsi `SUM(total_bayar)` di halaman `super_admin`.
   - Jika status masih `'Booked'` atau berubah jadi `'Cancelled'`, uang tersebut tidak akan dihitung sebagai omset pendapatan di dashboard Super Admin.

PAS PROJECT/
│
├── app.py                 # Core backend logic (Routing, Auth, DB Init)
├── database.db            # SQLite database file (Auto-generated)
│
└── templates/             # UI Templates
    ├── base.html          # Global layout (Tailwind CDN, Font, Shared Navbar/Sidebar)
    ├── login.html         # Elegant minimalist warm login form
    ├── dashboard_super.html# Analytics dashboard for Super Admin
    ├── dashboard_admin.html# Order management table for Receptionist
    └── dashboard_user.html # Catalog & booking form for Customera