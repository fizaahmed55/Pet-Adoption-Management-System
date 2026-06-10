"""
Professional Pet Adoption Management System
Oracle + Python CustomTkinter application

Use this as: PetAdoptionSystem/app/main.py
Requirements: customtkinter, oracledb, pillow
Database: pams / pams @ localhost:1521/ORCLPDB
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable
from decimal import Decimal
from datetime import date, datetime
from tkinter import ttk, messagebox

import customtkinter as ctk
import oracledb
from PIL import Image, ImageDraw, ImageFont


# -----------------------------------------------------------------------------
# ORACLE SETTINGS
# -----------------------------------------------------------------------------
ORACLE_USER = "pams"
ORACLE_PASSWORD = "pams"
ORACLE_DSN = "localhost:1521/ORCLPDB"

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


COLORS = {
    # Bright presentation palette: colorful but still clean/professional.
    "bg": "#FFF4E8",
    "panel": "#FFFFFF",
    "panel2": "#FFF9F0",
    "soft": "#FFE1C7",
    "line": "#FDBA74",
    "dark": "#102033",
    "muted": "#5F6B7A",
    "orange": "#FF6B1A",
    "orange2": "#EA580C",
    "rose": "#FF4D6D",
    "red": "#E11D48",
    "teal": "#00B4A6",
    "teal2": "#008C7E",
    "blue": "#2563EB",
    "green": "#22C55E",
    "green2": "#15803D",
    "purple": "#7C3AED",
    "yellow": "#F59E0B",
    "gray": "#F8FAFC",
    "sidebar": "#123B53",
    "sidebar2": "#1D536D",
    "sidebar_hover": "#245F7B",
    "sidebar_text": "#F8FAFC",
    "sidebar_muted": "#BFE7F1",
}


# -----------------------------------------------------------------------------
# UTILS
# -----------------------------------------------------------------------------

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().lower()


def display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return str(int(value))
        return f"{float(value):.2f}"
    return str(value)


def as_int(value: Any, default: int = 0) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(float(str(value).strip()))


def as_float(value: Any, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    return float(str(value).strip())


def sql_date(bind_name: str) -> str:
    return f"CASE WHEN :{bind_name} IS NULL THEN NULL ELSE TO_DATE(:{bind_name}, 'YYYY-MM-DD') END"


# -----------------------------------------------------------------------------
# DATABASE LAYER
# -----------------------------------------------------------------------------

class Database:
    def __init__(self) -> None:
        self.conn = oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN,
        )

    def all(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(sql, params or {})
            columns = [d[0].lower() for d in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def one(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: dict[str, Any] | None = None, default: Any = 0) -> Any:
        row = self.one(sql, params)
        if not row:
            return default
        return next(iter(row.values()))

    def run(self, sql: str, params: dict[str, Any] | None = None) -> int:
        with self.conn.cursor() as cur:
            cur.execute(sql, params or {})
            affected = cur.rowcount
        self.conn.commit()
        return affected

    def proc(self, name: str, args: list[Any]) -> None:
        with self.conn.cursor() as cur:
            cur.callproc(name, args)
        self.conn.commit()

    def transaction(self, work: Callable[[oracledb.Cursor], None]) -> None:
        try:
            with self.conn.cursor() as cur:
                work(cur)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise


# -----------------------------------------------------------------------------
# REUSABLE FORM DIALOG
# -----------------------------------------------------------------------------

class FormDialog(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, title: str, fields: list[dict[str, Any]], width: int = 620):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{width}x{max(430, 125 + len(fields) * 64)}")
        self.resizable(False, True)
        self.configure(fg_color=COLORS["bg"])
        self.transient(master)
        self.grab_set()
        self.result: dict[str, Any] | None = None
        self.widgets: dict[str, Any] = {}
        self.fields = fields

        card = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=28)
        card.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(card, text=title, text_color=COLORS["dark"], font=("Segoe UI", 26, "bold")).pack(
            anchor="w", padx=24, pady=(22, 10)
        )

        body = ctk.CTkScrollableFrame(card, fg_color="transparent", corner_radius=20)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        for f in fields:
            key = f["key"]
            label = f.get("label", key.replace("_", " ").title())
            ctk.CTkLabel(body, text=label, text_color=COLORS["dark"], font=("Segoe UI", 13, "bold")).pack(
                anchor="w", padx=8, pady=(10, 4)
            )
            ftype = f.get("type", "entry")
            default = f.get("default", "")
            if ftype == "combo":
                widget = ctk.CTkComboBox(
                    body,
                    values=f.get("values", []),
                    height=40,
                    corner_radius=14,
                    fg_color=COLORS["bg"],
                    border_color=COLORS["line"],
                    button_color=COLORS["orange"],
                    button_hover_color=COLORS["orange2"],
                    text_color=COLORS["dark"],
                )
                widget.pack(fill="x", padx=8)
                if default:
                    widget.set(default)
                elif f.get("values"):
                    widget.set(f["values"][0])
            elif ftype == "textbox":
                widget = ctk.CTkTextbox(body, height=f.get("height", 96), corner_radius=16, fg_color=COLORS["bg"], text_color=COLORS["dark"])
                widget.pack(fill="x", padx=8)
                if default:
                    widget.insert("1.0", str(default))
            elif ftype == "password":
                widget = ctk.CTkEntry(body, show="•", height=40, corner_radius=14, fg_color=COLORS["bg"], border_color=COLORS["line"], text_color=COLORS["dark"])
                widget.pack(fill="x", padx=8)
                if default:
                    widget.insert(0, str(default))
            else:
                widget = ctk.CTkEntry(body, height=40, corner_radius=14, fg_color=COLORS["bg"], border_color=COLORS["line"], text_color=COLORS["dark"], placeholder_text=f.get("placeholder", ""))
                widget.pack(fill="x", padx=8)
                if default is not None:
                    widget.insert(0, str(default))
            self.widgets[key] = widget

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(0, 22))
        ctk.CTkButton(buttons, text="Cancel", fg_color=COLORS["muted"], hover_color="#4B5563", corner_radius=16, command=self.cancel).pack(side="right", padx=(10, 0))
        ctk.CTkButton(buttons, text="Save", fg_color=COLORS["orange"], hover_color=COLORS["orange2"], corner_radius=16, command=self.save).pack(side="right")

        self.after(80, self.focus_first)
        self.bind("<Escape>", lambda _e: self.cancel())

    def focus_first(self) -> None:
        if self.widgets:
            try:
                next(iter(self.widgets.values())).focus_set()
            except Exception:
                pass

    def save(self) -> None:
        data: dict[str, Any] = {}
        for f in self.fields:
            key = f["key"]
            widget = self.widgets[key]
            if f.get("type") == "textbox":
                value = widget.get("1.0", "end").strip()
            else:
                value = widget.get().strip()
            if f.get("required") and not value:
                messagebox.showwarning("Required", f"Please enter {f.get('label', key)}.", parent=self)
                return
            data[key] = value if value != "" else None
        self.result = data
        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()


# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------

class PremiumPetAdoptionApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Fur Ever Paws - Pet Adoption Management System")
        self.geometry("1500x900")
        self.minsize(1280, 780)
        self.configure(fg_color=COLORS["bg"])

        self.db: Database | None = None
        self.user: dict[str, Any] | None = None
        self.page: ctk.CTkScrollableFrame | None = None
        self.sidebar: ctk.CTkFrame | None = None
        self.nav_area: ctk.CTkScrollableFrame | None = None
        self.image_cache: dict[str, ctk.CTkImage] = {}
        self.active_rows: list[dict[str, Any]] = []
        self.active_tree: ttk.Treeview | None = None

        self.show_login()

    # ------------------------- basics -------------------------
    def safe(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            messagebox.showerror("Operation failed", str(exc), parent=self)
            return None

    def connect_db(self) -> bool:
        if self.db is None:
            try:
                self.db = Database()
            except Exception as exc:
                messagebox.showerror(
                    "Oracle connection failed",
                    "The app could not connect to Oracle. Confirm that Oracle is running, PAMS user exists, and ORCLPDB is correct.\n\n"
                    f"Details:\n{exc}",
                    parent=self,
                )
                return False
        return True

    def clear_window(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()

    def clear_page(self) -> None:
        if self.page is None:
            return
        for widget in self.page.winfo_children():
            widget.destroy()
        self.active_rows = []
        self.active_tree = None

    def role(self) -> str:
        return self.user["role_name"] if self.user else ""

    def ask_form(self, title: str, fields: list[dict[str, Any]], width: int = 620) -> dict[str, Any] | None:
        dialog = FormDialog(self, title, fields, width)
        self.wait_window(dialog)
        return dialog.result

    def page_header(self, title: str, subtitle: str = "") -> None:
        assert self.page is not None
        ctk.CTkLabel(self.page, text=title, text_color=COLORS["dark"], font=("Segoe UI", 40, "bold")).pack(
            anchor="w", padx=34, pady=(30, 6)
        )
        if subtitle:
            ctk.CTkLabel(self.page, text=subtitle, text_color=COLORS["muted"], font=("Segoe UI", 17)).pack(
                anchor="w", padx=34, pady=(0, 22)
            )

    # ------------------------- image handling -------------------------
    def make_image(self, image_url: Any, name: str, category: str, size: tuple[int, int] = (385, 255)) -> ctk.CTkImage:
        key = f"{image_url}-{name}-{category}-{size}"
        if key in self.image_cache:
            return self.image_cache[key]

        image: Image.Image | None = None
        if image_url:
            p = Path(str(image_url))
            if not p.is_absolute():
                p = BASE_DIR / p
            if p.exists():
                try:
                    image = Image.open(p).convert("RGB")
                    image = self.cover_image(image, size)
                except Exception:
                    image = None

        if image is None:
            image = self.placeholder_image(name, category, size)

        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        self.image_cache[key] = ctk_image
        return ctk_image

    def cover_image(self, image: Image.Image, size: tuple[int, int]) -> Image.Image:
        """Fit the full pet picture inside the card without cropping important parts."""
        tw, th = size
        sw, sh = image.size
        scale = min(tw / sw, th / sh)
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        image = image.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGB", size, "#FFF7ED")
        canvas.paste(image, ((tw - nw) // 2, (th - nh) // 2))
        return canvas

    def placeholder_image(self, name: str, category: str, size: tuple[int, int]) -> Image.Image:
        palette = {
            "Dog": ("#FDBA74", "#EA580C"),
            "Cat": ("#F9A8D4", "#BE185D"),
            "Rabbit": ("#A7F3D0", "#047857"),
        }
        bg, fg = palette.get(category, ("#BFDBFE", "#2563EB"))
        image = Image.new("RGB", size, bg)
        draw = ImageDraw.Draw(image)
        w, h = size
        draw.ellipse((w - 130, -45, w + 45, 140), fill=fg)
        draw.ellipse((-55, h - 115, 125, h + 70), fill="#FFFFFF")
        draw.rounded_rectangle((16, 16, w - 16, h - 16), radius=26, outline="#FFFFFF", width=4)
        try:
            font_big = ImageFont.truetype("arial.ttf", 58)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()
        draw.text((30, 45), (name or "P")[0].upper(), fill=fg, font=font_big)
        draw.text((30, 120), category or "Pet", fill="#111827", font=font_small)
        return image

    # ------------------------- login -------------------------
    def show_login(self) -> None:
        self.clear_window()
        self.configure(fg_color=COLORS["bg"])

        root = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, weight=6, minsize=620)
        root.grid_columnconfigure(1, weight=5, minsize=520)
        root.grid_rowconfigure(0, weight=1)

        # Left presentation area. It is vertically scrollable only for small laptop screens.
        left = ctk.CTkScrollableFrame(
            root,
            fg_color=COLORS["bg"],
            corner_radius=0,
            scrollbar_button_color="#FDBA74",
            scrollbar_button_hover_color=COLORS["orange"],
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(38, 18), pady=42)

        brand = ctk.CTkFrame(left, fg_color=COLORS["soft"], corner_radius=26)
        brand.pack(anchor="w", pady=(8, 28))
        ctk.CTkLabel(
            brand,
            text="🐾  Fur Ever Paws",
            text_color=COLORS["orange2"],
            font=("Segoe UI", 28, "bold"),
            padx=24,
            pady=12,
        ).pack()

        ctk.CTkLabel(
            left,
            text="Fur Ever Paws\nAdoption Suite",
            text_color=COLORS["dark"],
            font=("Segoe UI", 46, "bold"),
            justify="left",
            wraplength=560,
        ).pack(anchor="w")

        quote = ctk.CTkFrame(left, fg_color="#FFF0D8", corner_radius=30)
        quote.pack(fill="x", pady=(30, 26))
        ctk.CTkLabel(
            quote,
            text="“Saving one pet will not change the world, but for that pet, the world changes forever.”",
            text_color=COLORS["dark"],
            font=("Segoe UI", 22, "bold"),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=28, pady=(24, 8))
        ctk.CTkLabel(
            quote,
            text="Responsible adoption • Safe shelters • Healthy pets",
            text_color=COLORS["teal2"],
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=28, pady=(0, 24))

        feature_row = ctk.CTkFrame(left, fg_color="transparent")
        feature_row.pack(fill="x", pady=(0, 12))
        feature_row.grid_columnconfigure(0, weight=1)
        feature_row.grid_columnconfigure(1, weight=1)

        login_features = [
            ("🐶", "Pet Gallery", "View pet records with images, breed, shelter, and adoption status."),
            ("🏠", "Home Checks", "Record adopter home verification before approval."),
            ("💉", "Pet Health", "Maintain medical and vaccination history."),
            ("📊", "Reports", "Review adoption, payment, donation, and health summaries."),
        ]
        feature_colors = ["#E0F2FE", "#DCFCE7", "#FFE4E6", "#F3E8FF"]
        feature_accent = [COLORS["blue"], COLORS["green2"], COLORS["rose"], COLORS["purple"]]
        for index, (icon, title, sub) in enumerate(login_features):
            card = ctk.CTkFrame(feature_row, fg_color=feature_colors[index], corner_radius=22, height=150)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=8, pady=8)
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 28)).pack(anchor="w", padx=18, pady=(14, 2))
            ctk.CTkLabel(card, text=title, text_color=feature_accent[index], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=18)
            ctk.CTkLabel(
                card,
                text=sub,
                text_color=COLORS["dark"],
                font=("Segoe UI", 13, "bold"),
                wraplength=230,
                justify="left",
            ).pack(anchor="w", padx=18, pady=(6, 14))

        # Right login panel.
        right = ctk.CTkFrame(root, fg_color=COLORS["panel"], corner_radius=36)
        right.grid(row=0, column=1, sticky="nsew", padx=(18, 42), pady=60)

        ctk.CTkLabel(
            right,
            text="Secure Login",
            text_color=COLORS["dark"],
            font=("Segoe UI", 40, "bold"),
        ).pack(anchor="w", padx=42, pady=(84, 34))

        email = ctk.CTkEntry(
            right,
            placeholder_text="Email address",
            height=54,
            corner_radius=16,
            fg_color=COLORS["bg"],
            border_color=COLORS["line"],
            text_color=COLORS["dark"],
            font=("Segoe UI", 15),
        )
        email.pack(fill="x", padx=42, pady=(0, 18))

        password = ctk.CTkEntry(
            right,
            placeholder_text="Password",
            show="•",
            height=54,
            corner_radius=16,
            fg_color=COLORS["bg"],
            border_color=COLORS["line"],
            text_color=COLORS["dark"],
            font=("Segoe UI", 15),
        )
        password.pack(fill="x", padx=42, pady=(0, 28))

        def do_login() -> None:
            if not self.connect_db():
                return
            assert self.db is not None
            row = self.db.one(
                """
                SELECT u.user_id, u.full_name, u.email, u.password_hash, r.role_name,
                       a.adopter_id, ss.staff_id, ss.shelter_id AS staff_shelter_id, v.vet_id
                FROM user_account u
                JOIN role r ON r.role_id = u.role_id
                LEFT JOIN adopter a ON a.user_id = u.user_id
                LEFT JOIN shelter_staff ss ON ss.user_id = u.user_id
                LEFT JOIN veterinarian v ON v.user_id = u.user_id
                WHERE LOWER(u.email) = LOWER(:email)
                  AND u.account_status = 'Active'
                """,
                {"email": email.get().strip()},
            )
            if not row or row["password_hash"] != sha256(password.get().strip()):
                messagebox.showerror("Login failed", "Invalid email or password.", parent=self)
                return
            self.user = row
            self.show_main()

        password.bind("<Return>", lambda _e: do_login())
        ctk.CTkButton(
            right,
            text="Login",
            height=56,
            corner_radius=18,
            fg_color=COLORS["orange"],
            hover_color=COLORS["orange2"],
            font=("Segoe UI", 17, "bold"),
            command=do_login,
        ).pack(fill="x", padx=42, pady=(4, 18))

        ctk.CTkLabel(
            right,
            text="Use your assigned system account.",
            text_color=COLORS["muted"],
            font=("Segoe UI", 14),
        ).pack(anchor="w", padx=42)

        divider = ctk.CTkFrame(right, fg_color=COLORS["line"], height=1)
        divider.pack(fill="x", padx=42, pady=(34, 22))

        ctk.CTkLabel(
            right,
            text="New adopter?",
            text_color=COLORS["dark"],
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", padx=42, pady=(0, 8))

        ctk.CTkButton(
            right,
            text="Create Adopter Account",
            height=50,
            corner_radius=18,
            fg_color=COLORS["teal"],
            hover_color=COLORS["teal2"],
            font=("Segoe UI", 16, "bold"),
            command=self.show_registration,
        ).pack(fill="x", padx=42, pady=(0, 10))

        ctk.CTkLabel(
            right,
            text="Staff and veterinarian accounts are created by the administrator.",
            text_color=COLORS["muted"],
            font=("Segoe UI", 13),
            wraplength=470,
            justify="left",
        ).pack(anchor="w", padx=42)

    def show_registration(self) -> None:
        self.clear_window()
        self.configure(fg_color=COLORS["bg"])

        root = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, weight=5, minsize=500)
        root.grid_columnconfigure(1, weight=6, minsize=620)
        root.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(root, fg_color=COLORS["bg"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(48, 24), pady=58)

        brand = ctk.CTkFrame(left, fg_color=COLORS["soft"], corner_radius=26)
        brand.pack(anchor="w", pady=(0, 26))
        ctk.CTkLabel(brand, text="🐾  Fur Ever Paws", text_color=COLORS["orange2"], font=("Segoe UI", 28, "bold"), padx=24, pady=12).pack()

        ctk.CTkLabel(
            left,
            text="Create your\nadopter profile",
            text_color=COLORS["dark"],
            font=("Segoe UI", 48, "bold"),
            justify="left",
            wraplength=500,
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text="Register to browse pets, submit adoption applications, track approval progress, and give feedback after adoption.",
            text_color=COLORS["muted"],
            font=("Segoe UI", 18, "bold"),
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(18, 26))

        info = ctk.CTkFrame(left, fg_color=COLORS["panel"], corner_radius=28)
        info.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(info, text="Account Type", text_color=COLORS["teal2"], font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=24, pady=(22, 4))
        ctk.CTkLabel(info, text="Self-registration is only for adopters. Staff and veterinarian accounts are created by the administrator so system access remains controlled.", text_color=COLORS["dark"], font=("Segoe UI", 15), wraplength=430, justify="left").pack(anchor="w", padx=24, pady=(0, 22))

        form_card = ctk.CTkFrame(root, fg_color=COLORS["panel"], corner_radius=36)
        form_card.grid(row=0, column=1, sticky="nsew", padx=(20, 48), pady=42)

        ctk.CTkLabel(form_card, text="Adopter Registration", text_color=COLORS["dark"], font=("Segoe UI", 34, "bold")).pack(anchor="w", padx=42, pady=(36, 6))
        ctk.CTkLabel(form_card, text="Fill in your details to create an adopter account.", text_color=COLORS["muted"], font=("Segoe UI", 15)).pack(anchor="w", padx=42, pady=(0, 18))

        body = ctk.CTkScrollableFrame(form_card, fg_color="transparent", corner_radius=20)
        body.pack(fill="both", expand=True, padx=34, pady=(0, 12))

        def add_entry(label: str, placeholder: str = "", show: str | None = None) -> ctk.CTkEntry:
            ctk.CTkLabel(body, text=label, text_color=COLORS["dark"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=8, pady=(10, 4))
            entry = ctk.CTkEntry(body, placeholder_text=placeholder, show=show, height=42, corner_radius=14, fg_color=COLORS["bg"], border_color=COLORS["line"], text_color=COLORS["dark"], font=("Segoe UI", 14))
            entry.pack(fill="x", padx=8)
            return entry

        full_name = add_entry("Full Name", "Ayesha Khan")
        email = add_entry("Email", "ayesha@example.com")
        phone = add_entry("Phone Number", "03001234567")
        password = add_entry("Password", "Minimum 6 characters", show="•")
        confirm_password = add_entry("Confirm Password", "Repeat password", show="•")
        occupation = add_entry("Occupation", "Student / Teacher / Engineer")

        ctk.CTkLabel(body, text="Residence Type", text_color=COLORS["dark"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=8, pady=(10, 4))
        residence = ctk.CTkComboBox(body, values=["House", "Apartment", "Hostel", "Farm House", "Other"], height=42, corner_radius=14, fg_color=COLORS["bg"], border_color=COLORS["line"], button_color=COLORS["orange"], button_hover_color=COLORS["orange2"], text_color=COLORS["dark"], font=("Segoe UI", 14))
        residence.pack(fill="x", padx=8)
        residence.set("House")

        ctk.CTkLabel(body, text="Do you already have pets?", text_color=COLORS["dark"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=8, pady=(10, 4))
        has_pets = ctk.CTkComboBox(body, values=["N", "Y"], height=42, corner_radius=14, fg_color=COLORS["bg"], border_color=COLORS["line"], button_color=COLORS["orange"], button_hover_color=COLORS["orange2"], text_color=COLORS["dark"], font=("Segoe UI", 14))
        has_pets.pack(fill="x", padx=8)
        has_pets.set("N")

        buttons = ctk.CTkFrame(form_card, fg_color="transparent")
        buttons.pack(fill="x", padx=42, pady=(0, 32))

        def create_account() -> None:
            if not self.connect_db():
                return
            assert self.db is not None
            name_val = full_name.get().strip()
            email_val = email.get().strip().lower()
            pass_val = password.get().strip()
            confirm_val = confirm_password.get().strip()

            if not name_val or not email_val or not pass_val:
                messagebox.showwarning("Required", "Full name, email, and password are required.", parent=self)
                return
            if "@" not in email_val or "." not in email_val:
                messagebox.showwarning("Invalid email", "Please enter a valid email address.", parent=self)
                return
            if len(pass_val) < 6:
                messagebox.showwarning("Weak password", "Password must be at least 6 characters.", parent=self)
                return
            if pass_val != confirm_val:
                messagebox.showwarning("Password mismatch", "Password and confirm password do not match.", parent=self)
                return
            if self.db.scalar("SELECT COUNT(*) FROM user_account WHERE LOWER(email)=LOWER(:email)", {"email": email_val}):
                messagebox.showwarning("Email exists", "An account with this email already exists.", parent=self)
                return

            role_row = self.db.one("SELECT role_id FROM role WHERE role_name='Adopter'")
            if not role_row:
                messagebox.showerror("Setup missing", "The Adopter role is missing from the ROLE table.", parent=self)
                return

            def work(cur: oracledb.Cursor) -> None:
                user_var = cur.var(oracledb.NUMBER)
                cur.execute(
                    """
                    INSERT INTO user_account(full_name, email, password_hash, phone_no, account_status, role_id)
                    VALUES(:full_name, :email, :password_hash, :phone_no, 'Active', :role_id)
                    RETURNING user_id INTO :user_id
                    """,
                    {
                        "full_name": name_val,
                        "email": email_val,
                        "password_hash": sha256(pass_val),
                        "phone_no": phone.get().strip() or None,
                        "role_id": role_row["role_id"],
                        "user_id": user_var,
                    },
                )
                user_id = int(user_var.getvalue()[0])
                cur.execute(
                    """
                    INSERT INTO adopter(user_id, occupation, residence_type, has_other_pets, adopter_status)
                    VALUES(:user_id, :occupation, :residence_type, :has_other_pets, 'Verified')
                    """,
                    {
                        "user_id": user_id,
                        "occupation": occupation.get().strip() or None,
                        "residence_type": residence.get().strip() or None,
                        "has_other_pets": has_pets.get().strip() or "N",
                    },
                )

            try:
                self.db.transaction(work)
                messagebox.showinfo("Account created", "Your adopter account has been created. You can now log in.", parent=self)
                self.show_login()
            except Exception as exc:
                messagebox.showerror("Registration failed", str(exc), parent=self)

        ctk.CTkButton(buttons, text="Back to Login", height=50, corner_radius=18, fg_color=COLORS["muted"], hover_color="#4B5563", font=("Segoe UI", 15, "bold"), command=self.show_login).pack(side="left")
        ctk.CTkButton(buttons, text="Create Account", height=50, corner_radius=18, fg_color=COLORS["orange"], hover_color=COLORS["orange2"], font=("Segoe UI", 15, "bold"), command=create_account).pack(side="right")

    # ------------------------- main shell -------------------------
    def show_main(self) -> None:
        self.clear_window()
        self.configure(fg_color=COLORS["bg"])

        # Fixed sidebar shell + scrollable navigation area.
        # This keeps the brand/profile visible and lets all role menus scroll cleanly.
        self.sidebar = ctk.CTkFrame(self, width=310, fg_color=COLORS["sidebar"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(24, 14))
        ctk.CTkLabel(brand, text="🐾 Fur Ever Paws", text_color="#FFFFFF", font=("Segoe UI", 32, "bold")).pack(
            anchor="w"
        )
        ctk.CTkLabel(brand, text="Pet Adoption Management System", text_color=COLORS["sidebar_muted"], font=("Segoe UI", 14, "bold")).pack(
            anchor="w", pady=(2, 0)
        )

        assert self.user is not None
        profile = ctk.CTkFrame(self.sidebar, fg_color=COLORS["sidebar2"], corner_radius=24)
        profile.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(profile, text="👤", font=("Segoe UI", 32)).pack(anchor="w", padx=20, pady=(16, 0))
        ctk.CTkLabel(profile, text=self.user["full_name"], text_color="#FFFFFF", font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=20)
        ctk.CTkLabel(profile, text=self.user["role_name"], text_color="#99F6E4", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkLabel(self.sidebar, text="MENU", text_color=COLORS["sidebar_muted"], font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=24, pady=(0, 6)
        )
        self.nav_area = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=COLORS["orange"],
            scrollbar_button_hover_color=COLORS["orange2"],
        )
        self.nav_area.pack(fill="both", expand=True, padx=0, pady=(0, 10))

        self.nav("🏡  Home", self.show_home)

        if self.role() == "Admin":
            self.nav("🐾  Pet Gallery", self.show_pets)
            self.nav("➕  Add Pet", self.add_pet_dialog)
            self.nav("🧬  Pet Types & Breeds", self.show_pet_types)
            self.nav("📋  Applications", self.show_applications)
            self.nav("🏠  Home Checks", self.show_home_checks)
            self.nav("✅  Adoptions", self.show_adoptions)
            self.nav("📄  Documents", self.show_documents)
            self.nav("💳  Payments", self.show_payments)
            self.nav("💝  Donations", self.show_donations)
            self.nav("🩺  Medical", self.show_medical)
            self.nav("💉  Vaccinations", self.show_vaccinations)
            self.nav("👥  Users", self.show_users)
            self.nav("🏢  Shelters", self.show_shelters)
            self.nav("📊  Reports", self.show_reports)

        elif self.role() == "Shelter Staff":
            self.nav("🐾  Pet Gallery", self.show_pets)
            self.nav("➕  Add Pet", self.add_pet_dialog)
            self.nav("🧬  Pet Types & Breeds", self.show_pet_types)
            self.nav("📋  Applications", self.show_applications)
            self.nav("🏠  Home Checks", self.show_home_checks)
            self.nav("✅  Adoptions", self.show_adoptions)
            self.nav("📄  Documents", self.show_documents)
            self.nav("💳  Payments", self.show_payments)
            self.nav("💝  Donations", self.show_donations)
            self.nav("📊  Reports", self.show_reports)

        elif self.role() == "Veterinarian":
            self.nav("🐾  Pet Gallery", self.show_pets)
            self.nav("🩺  Medical", self.show_medical)
            self.nav("💉  Vaccinations", self.show_vaccinations)
            self.nav("📊  Health Reports", self.show_reports)

        elif self.role() == "Adopter":
            self.nav("🐾  Pet Gallery", self.show_pets)
            self.nav("📋  My Applications", self.show_applications)
            self.nav("📄  My Document Status", self.show_documents)
            self.nav("✅  My Adoptions & Feedback", self.show_adoptions)

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkButton(
            footer,
            text="Logout",
            height=46,
            corner_radius=18,
            fg_color=COLORS["rose"],
            hover_color=COLORS["red"],
            font=("Segoe UI", 15, "bold"),
            command=self.show_login,
        ).pack(fill="x")

        self.page = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.page.pack(side="right", fill="both", expand=True)
        self.show_home()

    def nav(self, text: str, command: Callable[[], None]) -> None:
        assert self.nav_area is not None
        ctk.CTkButton(
            self.nav_area,
            text=text,
            anchor="w",
            height=48,
            corner_radius=18,
            fg_color="transparent",
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["sidebar_text"],
            font=("Segoe UI", 16, "bold"),
            command=lambda: self.safe(command),
        ).pack(fill="x", padx=16, pady=5)

    # ------------------------- table component -------------------------
    def render_table(self, rows: list[dict[str, Any]], columns: list[str], height: int = 18) -> ttk.Treeview:
        assert self.page is not None
        wrapper = ctk.CTkFrame(self.page, fg_color=COLORS["panel"], corner_radius=28)
        wrapper.pack(fill="both", expand=True, padx=30, pady=(0, 30))

        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure("Treeview", rowheight=48, background="#FFFFFF", foreground="#1F2937", fieldbackground="#FFFFFF", font=("Segoe UI", 14), borderwidth=0)
        style.configure("Treeview.Heading", background="#FFEDD5", foreground="#9A3412", font=("Segoe UI", 14, "bold"))
        style.map("Treeview", background=[("selected", "#FDBA74")])

        tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=height)
        y_scroll = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(wrapper, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        for col in columns:
            tree.heading(col, text=col.replace("_", " ").title())
            width = 145
            if "name" in col or "email" in col:
                width = 190
            if "description" in col or "reason" in col or "remarks" in col:
                width = 280
            if col.endswith("id") or col in {"age", "rating"}:
                width = 90
            tree.column(col, width=width, anchor="center")

        if rows:
            for row in rows:
                tree.insert("", "end", values=[display(row.get(c)) for c in columns])
        else:
            tree.insert("", "end", values=["No records found"] + [""] * (len(columns) - 1))

        tree.grid(row=0, column=0, sticky="nsew", padx=(16, 0), pady=(16, 0))
        y_scroll.grid(row=0, column=1, sticky="ns", pady=(16, 0), padx=(0, 16))
        x_scroll.grid(row=1, column=0, sticky="ew", padx=(16, 0), pady=(0, 16))
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        self.active_rows = rows
        self.active_tree = tree
        return tree

    def selected_row(self) -> dict[str, Any] | None:
        if not self.active_tree:
            messagebox.showwarning("Select row", "No table is active.", parent=self)
            return None
        selected = self.active_tree.selection()
        if not selected:
            messagebox.showwarning("Select row", "Please select a row first.", parent=self)
            return None
        idx = self.active_tree.index(selected[0])
        if 0 <= idx < len(self.active_rows):
            return self.active_rows[idx]
        return None

    def toolbar(self) -> ctk.CTkFrame:
        assert self.page is not None
        bar = ctk.CTkFrame(self.page, fg_color=COLORS["panel"], corner_radius=24)
        bar.pack(fill="x", padx=30, pady=(0, 18))
        return bar

    def add_action(self, parent: ctk.CTkFrame, text: str, command: Callable[[], None], color: str | None = None) -> None:
        ctk.CTkButton(
            parent,
            text=text,
            height=42,
            corner_radius=16,
            fg_color=color or COLORS["orange"],
            hover_color=COLORS["orange2"],
            command=lambda: self.safe(command),
        ).pack(side="left", padx=(16 if not parent.winfo_children() else 0, 8), pady=16)

    # ------------------------- home -------------------------
    def show_home(self) -> None:
        self.clear_page()
        assert self.user is not None and self.db is not None
        role = self.role()
        self.page_header("Home", f"Welcome, {self.user['full_name']}. Your {self.user['role_name']} workspace is ready.")

        hero = ctk.CTkFrame(self.page, fg_color=COLORS["orange"], corner_radius=34)
        hero.pack(fill="x", padx=30, pady=(0, 22))
        ctk.CTkLabel(
            hero,
            text="Every adoption deserves a careful process.",
            text_color="#FFFFFF",
            font=("Segoe UI", 38, "bold"),
        ).pack(anchor="w", padx=34, pady=(28, 6))
        ctk.CTkLabel(
            hero,
            text="Fur Ever Paws protects adopter privacy and separates responsibilities for adopters, staff, veterinarians, and administrators.",
            text_color="#FFF7ED",
            font=("Segoe UI", 21, "bold"),
            wraplength=1050,
        ).pack(anchor="w", padx=34, pady=(0, 28))

        stats = ctk.CTkFrame(self.page, fg_color="transparent")
        stats.pack(fill="x", padx=30, pady=(0, 24))

        if role == "Adopter":
            adopter_id = self.user.get("adopter_id")
            cards = [
                ("🐶", "Available Pets", "SELECT COUNT(*) FROM pet WHERE availability_status='Available'", {}, COLORS["teal"]),
                ("📋", "My Applications", "SELECT COUNT(*) FROM adoption_application WHERE adopter_id=:adopter_id", {"adopter_id": adopter_id}, COLORS["blue"]),
                ("✅", "My Completed Adoptions", """
                    SELECT COUNT(*)
                    FROM adoption_record ar
                    JOIN adoption_application aa ON aa.application_id = ar.application_id
                    WHERE aa.adopter_id=:adopter_id AND ar.adoption_status='Completed'
                """, {"adopter_id": adopter_id}, COLORS["green"]),
                ("📄", "My Document Records", """
                    SELECT COUNT(*)
                    FROM application_document doc
                    JOIN adoption_application aa ON aa.application_id = doc.application_id
                    WHERE aa.adopter_id=:adopter_id
                """, {"adopter_id": adopter_id}, COLORS["purple"]),
            ]
            flow_items = [
                ("1", "Browse", "View available pets."),
                ("2", "Apply", "Fill the adoption form."),
                ("3", "Staff Review", "Staff handles documents and home check."),
                ("4", "Vet Check", "Vet confirms health and vaccination."),
                ("5", "Final Result", "Admin finalizes successful adoption."),
            ]
        elif role == "Shelter Staff":
            shelter_id = self.user.get("staff_shelter_id")
            cards = [
                ("🐾", "Shelter Pets", "SELECT COUNT(*) FROM pet WHERE shelter_id=:shelter_id", {"shelter_id": shelter_id}, COLORS["teal"]),
                ("📋", "Shelter Applications", """
                    SELECT COUNT(*) FROM adoption_application aa
                    JOIN pet p ON p.pet_id=aa.pet_id
                    WHERE p.shelter_id=:shelter_id
                """, {"shelter_id": shelter_id}, COLORS["blue"]),
                ("🏠", "Home Checks", """
                    SELECT COUNT(*) FROM home_check hc
                    JOIN adoption_application aa ON aa.application_id=hc.application_id
                    JOIN pet p ON p.pet_id=aa.pet_id
                    WHERE p.shelter_id=:shelter_id
                """, {"shelter_id": shelter_id}, COLORS["green"]),
                ("📄", "Documents", """
                    SELECT COUNT(*) FROM application_document doc
                    JOIN adoption_application aa ON aa.application_id=doc.application_id
                    JOIN pet p ON p.pet_id=aa.pet_id
                    WHERE p.shelter_id=:shelter_id
                """, {"shelter_id": shelter_id}, COLORS["purple"]),
            ]
            flow_items = [
                ("1", "Review", "Check shelter applications."),
                ("2", "Documents", "Create/verify application documents."),
                ("3", "Home Check", "Record suitability result."),
                ("4", "Reserve", "Recommend and reserve pet."),
                ("5", "Admin", "Admin completes final adoption."),
            ]
        elif role == "Veterinarian":
            cards = [
                ("🐾", "Pets", "SELECT COUNT(*) FROM pet", {}, COLORS["teal"]),
                ("🩺", "Medical Records", "SELECT COUNT(*) FROM medical_record", {}, COLORS["blue"]),
                ("💉", "Vaccination Records", "SELECT COUNT(*) FROM vaccination_record", {}, COLORS["green"]),
                ("⚠️", "Needs Care", "SELECT COUNT(*) FROM pet WHERE health_status IN ('Under Treatment','Vaccination Due','Critical')", {}, COLORS["rose"]),
            ]
            flow_items = [
                ("1", "View Pets", "Open pet health list."),
                ("2", "Medical", "Add diagnosis and treatment."),
                ("3", "Vaccination", "Record vaccine and due date."),
                ("4", "Status", "Update health status."),
                ("5", "Clearance", "Healthy pets move forward."),
            ]
        else:
            cards = [
                ("🐶", "Available Pets", "SELECT COUNT(*) FROM pet WHERE availability_status='Available'", {}, COLORS["teal"]),
                ("📋", "Applications", "SELECT COUNT(*) FROM adoption_application", {}, COLORS["blue"]),
                ("🏠", "Completed Adoptions", "SELECT COUNT(*) FROM adoption_record WHERE adoption_status='Completed'", {}, COLORS["green"]),
                ("💝", "Donations", "SELECT NVL(SUM(amount),0) FROM donation", {}, COLORS["purple"]),
            ]
            flow_items = [
                ("1", "Apply", "Adopter submits application form."),
                ("2", "Documents", "Staff creates and verifies documents."),
                ("3", "Home Check", "Staff records suitability."),
                ("4", "Vet Check", "Vet adds health and vaccine records."),
                ("5", "Finalize", "Admin records final adoption and payment."),
            ]

        for icon, label, sql, params, color in cards:
            value = self.db.scalar(sql, params)
            card = ctk.CTkFrame(stats, fg_color=COLORS["panel"], corner_radius=26)
            card.pack(side="left", fill="x", expand=True, padx=(0, 14))
            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 34)).pack(anchor="w", padx=24, pady=(20, 0))
            ctk.CTkLabel(card, text=display(value), text_color=color, font=("Segoe UI", 36, "bold")).pack(anchor="w", padx=24)
            ctk.CTkLabel(card, text=label, text_color=COLORS["muted"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=24, pady=(0, 20))

        ctk.CTkLabel(self.page, text="Workflow", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
        flow = ctk.CTkFrame(self.page, fg_color="transparent")
        flow.pack(fill="x", padx=30, pady=(0, 24))
        for n, title, text in flow_items:
            box = ctk.CTkFrame(flow, fg_color=COLORS["panel"], corner_radius=24)
            box.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ctk.CTkLabel(box, text=n, fg_color=COLORS["soft"], text_color=COLORS["orange2"], corner_radius=20, width=48, height=48, font=("Segoe UI", 21, "bold")).pack(anchor="w", padx=18, pady=(18, 8))
            ctk.CTkLabel(box, text=title, text_color=COLORS["dark"], font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=20)
            ctk.CTkLabel(box, text=text, text_color=COLORS["muted"], font=("Segoe UI", 15), wraplength=215, justify="left").pack(anchor="w", padx=20, pady=(6, 22))

        if role in ("Admin", "Shelter Staff"):
            ctk.CTkLabel(self.page, text="Recent Adoption Pipeline", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(2, 8))
            rows = self.application_rows()[:8]
            self.render_table(rows, ["application_id", "adopter_name", "pet_name", "shelter_name", "application_status", "home_status", "adoption_status"], height=10)
        elif role == "Adopter":
            ctk.CTkLabel(self.page, text="My Recent Applications", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(2, 8))
            rows = self.application_rows()[:8]
            self.render_table(rows, ["application_id", "pet_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_status"], height=10)
        elif role == "Veterinarian":
            ctk.CTkLabel(self.page, text="Pet Health Summary", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(2, 8))
            rows = self.db.all("SELECT * FROM vw_pet_health_summary ORDER BY pet_id")
            self.render_table(rows, ["pet_id", "pet_name", "health_status", "last_checkup", "last_vaccination", "next_vaccine_due"], height=10)


    def pet_rows(self) -> list[dict[str, Any]]:
        assert self.db is not None
        return self.db.all(
            """
            SELECT p.pet_id, p.pet_name, p.age, p.gender, p.color, p.size_label,
                   p.health_status, p.availability_status, p.description, p.shelter_id, p.breed_id,
                   b.breed_name, c.category_name, s.shelter_name,
                   (SELECT image_url FROM pet_image pi WHERE pi.pet_id = p.pet_id AND ROWNUM = 1) AS image_url
            FROM pet p
            JOIN breed b ON b.breed_id = p.breed_id
            JOIN pet_category c ON c.category_id = b.category_id
            JOIN shelter s ON s.shelter_id = p.shelter_id
            ORDER BY p.pet_id
            """
        )

    def show_pets(self) -> None:
        self.clear_page()
        self.page_header("Pet Gallery", "Large readable pet cards with full image display, breed, shelter, health, and adoption status.")

        bar = self.toolbar()
        if self.role() in ("Admin", "Shelter Staff"):
            self.add_action(bar, "Add Pet", self.add_pet_dialog, COLORS["orange"])
            self.add_action(bar, "Update Selected Status", self.update_pet_status, COLORS["teal"])
            self.add_action(bar, "Add Image", self.add_pet_image, COLORS["purple"])
        self.add_action(bar, "Refresh", self.show_pets, COLORS["blue"])

        rows = self.pet_rows()
        grid = ctk.CTkFrame(self.page, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=30, pady=(0, 28))
        gallery_columns = 2
        for i, pet in enumerate(rows):
            card = self.pet_card(grid, pet)
            card.grid(row=i // gallery_columns, column=i % gallery_columns, sticky="nsew", padx=14, pady=14)
        for col in range(gallery_columns):
            grid.grid_columnconfigure(col, weight=1)

    def pet_card(self, parent: ctk.CTkFrame, pet: dict[str, Any]) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=28)
        img = self.make_image(pet.get("image_url"), pet.get("pet_name", "Pet"), pet.get("category_name", "Pet"), size=(420, 275))
        ctk.CTkLabel(card, image=img, text="").pack(fill="x", padx=14, pady=(14, 10))

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18)
        ctk.CTkLabel(top, text=pet["pet_name"], text_color=COLORS["dark"], font=("Segoe UI", 26, "bold")).pack(side="left")
        status_color = COLORS["green"] if pet["availability_status"] == "Available" else COLORS["yellow"]
        ctk.CTkLabel(top, text=pet["availability_status"], fg_color=status_color, text_color="#FFFFFF", corner_radius=12, padx=10, pady=4, font=("Segoe UI", 11, "bold")).pack(side="right")

        detail = f"{pet['category_name']} • {pet['breed_name']} • {pet['gender']} • {display(pet['age'])} yrs"
        ctk.CTkLabel(card, text=detail, text_color=COLORS["muted"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(6, 2))
        ctk.CTkLabel(card, text=f"Shelter: {pet['shelter_name']}", text_color=COLORS["teal2"], font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(0, 10))
        desc = display(pet.get("description")) or "Ready for a loving home."
        ctk.CTkLabel(card, text=desc[:95] + ("..." if len(desc) > 95 else ""), text_color=COLORS["muted"], font=("Segoe UI", 14), wraplength=405, justify="left").pack(anchor="w", padx=18, pady=(0, 14))

        if self.role() == "Adopter" and pet["availability_status"] == "Available":
            ctk.CTkButton(card, text="Apply for Adoption", fg_color=COLORS["orange"], hover_color=COLORS["orange2"], corner_radius=16, command=lambda p=pet: self.apply_for_pet(p)).pack(fill="x", padx=18, pady=(0, 18))
        else:
            ctk.CTkLabel(card, text=f"Pet ID: {pet['pet_id']}", text_color=COLORS["muted"], font=("Segoe UI", 12)).pack(anchor="w", padx=18, pady=(0, 18))
        return card

    def add_pet_dialog(self) -> None:
        assert self.db is not None
        shelters = self.db.all("SELECT shelter_id, shelter_name FROM shelter ORDER BY shelter_id")
        breeds = self.db.all(
            """
            SELECT b.breed_id, b.breed_name, c.category_name
            FROM breed b JOIN pet_category c ON c.category_id = b.category_id
            ORDER BY c.category_name, b.breed_name
            """
        )
        shelter_opts = {f"{r['shelter_id']} - {r['shelter_name']}": r["shelter_id"] for r in shelters}
        breed_opts = {f"{r['breed_id']} - {r['category_name']} / {r['breed_name']}": r["breed_id"] for r in breeds}
        data = self.ask_form(
            "Add Pet",
            [
                {"key": "pet_name", "label": "Pet Name", "required": True},
                {"key": "age", "label": "Age", "default": "1", "required": True},
                {"key": "gender", "label": "Gender", "type": "combo", "values": ["Male", "Female", "Unknown"]},
                {"key": "color", "label": "Color"},
                {"key": "size_label", "label": "Size", "type": "combo", "values": ["Small", "Medium", "Large"]},
                {"key": "rescue_date", "label": "Rescue Date (YYYY-MM-DD)", "placeholder": "2026-06-01"},
                {"key": "health_status", "label": "Health", "type": "combo", "values": ["Healthy", "Under Treatment", "Vaccination Due", "Critical"]},
                {"key": "availability_status", "label": "Availability", "type": "combo", "values": ["Available", "Reserved", "Adopted", "Unavailable"]},
                {"key": "shelter", "label": "Shelter", "type": "combo", "values": list(shelter_opts), "required": True},
                {"key": "breed", "label": "Pet Type / Breed", "type": "combo", "values": list(breed_opts), "required": True},
                {"key": "image_url", "label": "Image Path", "placeholder": "assets/buddy.jpg"},
                {"key": "description", "label": "Description", "type": "textbox"},
            ],
            width=720,
        )
        if not data:
            return

        def work(cur: oracledb.Cursor) -> None:
            pet_var = cur.var(oracledb.NUMBER)
            cur.execute(
                f"""
                INSERT INTO pet(pet_name, age, gender, color, size_label, rescue_date, description,
                                health_status, availability_status, shelter_id, breed_id)
                VALUES(:pet_name, :age, :gender, :color, :size_label, {sql_date('rescue_date')}, :description,
                       :health_status, :availability_status, :shelter_id, :breed_id)
                RETURNING pet_id INTO :pet_id
                """,
                {
                    "pet_name": data["pet_name"],
                    "age": as_float(data["age"]),
                    "gender": data["gender"],
                    "color": data["color"],
                    "size_label": data["size_label"],
                    "rescue_date": data["rescue_date"],
                    "description": data["description"],
                    "health_status": data["health_status"],
                    "availability_status": data["availability_status"],
                    "shelter_id": shelter_opts[data["shelter"]],
                    "breed_id": breed_opts[data["breed"]],
                    "pet_id": pet_var,
                },
            )
            pet_id = int(pet_var.getvalue()[0])
            if data.get("image_url"):
                cur.execute("INSERT INTO pet_image(pet_id, image_url) VALUES(:pet_id, :url)", {"pet_id": pet_id, "url": data["image_url"]})

        self.db.transaction(work)
        messagebox.showinfo("Saved", "Pet added successfully.", parent=self)
        self.show_pets()

    def update_pet_status(self) -> None:
        rows = self.pet_rows()
        self.clear_page()
        self.page_header("Update Pet Status", "Select a pet row, then update its health or availability status.")
        bar = self.toolbar()
        self.add_action(bar, "Update Selected", self._update_pet_status_selected, COLORS["teal"])
        self.add_action(bar, "Back to Gallery", self.show_pets, COLORS["blue"])
        self.render_table(rows, ["pet_id", "pet_name", "category_name", "breed_name", "health_status", "availability_status", "shelter_name"])

    def _update_pet_status_selected(self) -> None:
        assert self.db is not None
        row = self.selected_row()
        if not row:
            return
        data = self.ask_form(
            f"Update {row['pet_name']}",
            [
                {"key": "availability_status", "label": "Availability", "type": "combo", "values": ["Available", "Reserved", "Adopted", "Unavailable"], "default": row["availability_status"]},
                {"key": "health_status", "label": "Health", "type": "combo", "values": ["Healthy", "Under Treatment", "Vaccination Due", "Critical"], "default": row["health_status"]},
            ],
        )
        if not data:
            return
        self.db.run(
            "UPDATE pet SET availability_status=:availability_status, health_status=:health_status WHERE pet_id=:pet_id",
            {"availability_status": data["availability_status"], "health_status": data["health_status"], "pet_id": row["pet_id"]},
        )
        self.update_pet_status()

    def add_pet_image(self) -> None:
        rows = self.pet_rows()
        self.clear_page()
        self.page_header("Add Pet Image", "Select a pet row, then attach an image path such as assets/buddy.jpg.")
        bar = self.toolbar()
        self.add_action(bar, "Add Image to Selected", self._add_pet_image_selected, COLORS["purple"])
        self.add_action(bar, "Back to Gallery", self.show_pets, COLORS["blue"])
        self.render_table(rows, ["pet_id", "pet_name", "category_name", "breed_name", "image_url"])

    def _add_pet_image_selected(self) -> None:
        assert self.db is not None
        row = self.selected_row()
        if not row:
            return
        data = self.ask_form("Add Image", [{"key": "image_url", "label": "Image Path", "required": True, "placeholder": "assets/buddy.jpg"}])
        if not data:
            return
        self.db.run("INSERT INTO pet_image(pet_id, image_url) VALUES(:pet_id, :image_url)", {"pet_id": row["pet_id"], "image_url": data["image_url"]})
        self.show_pets()

    def apply_for_pet(self, pet: dict[str, Any]) -> None:
        assert self.db is not None and self.user is not None
        if not self.user.get("adopter_id"):
            messagebox.showwarning("Adopter only", "Only adopters can submit applications.", parent=self)
            return
        if pet.get("availability_status") != "Available":
            messagebox.showwarning("Not available", "This pet is not currently available for adoption.", parent=self)
            return

        data = self.ask_form(
            f"Adoption Application for {pet['pet_name']}",
            [
                {"key": "reason", "label": "Why do you want to adopt this pet?", "type": "textbox", "required": True, "height": 110},
                {"key": "home_environment", "label": "Home Environment", "type": "combo", "values": ["Apartment", "House", "House with Yard", "Farm", "Other"], "default": "Apartment"},
                {"key": "experience", "label": "Previous Pet Experience", "type": "combo", "values": ["No previous experience", "Some experience", "Experienced owner"], "default": "Some experience"},
                {"key": "care_plan", "label": "Daily Care Plan", "type": "textbox", "required": True, "height": 90},
            ],
            width=720,
        )
        if not data:
            return

        active = self.db.scalar(
            """
            SELECT COUNT(*) FROM adoption_application
            WHERE adopter_id=:adopter_id AND pet_id=:pet_id AND application_status IN ('Pending','Approved')
            """,
            {"adopter_id": self.user["adopter_id"], "pet_id": pet["pet_id"]},
        )
        if active:
            messagebox.showwarning("Already applied", "You already have an active application for this pet.", parent=self)
            return

        reason_text = (
            f"Reason: {data['reason']}\n\n"
            f"Home Environment: {data['home_environment']}\n"
            f"Previous Pet Experience: {data['experience']}\n"
            f"Daily Care Plan: {data['care_plan']}"
        )

        self.db.run(
            """
            INSERT INTO adoption_application(adopter_id, pet_id, application_date, reason_for_adoption, application_status)
            VALUES(:adopter_id, :pet_id, SYSDATE, :reason, 'Pending')
            """,
            {"adopter_id": self.user["adopter_id"], "pet_id": pet["pet_id"], "reason": reason_text},
        )
        messagebox.showinfo(
            "Application Submitted",
            "Your application form has been submitted. Shelter staff will create and verify application documents during review.",
            parent=self,
        )
        self.show_applications()


    def application_rows(self) -> list[dict[str, Any]]:
        assert self.db is not None and self.user is not None
        sql = """
            SELECT aa.application_id, aa.adopter_id, u.full_name AS adopter_name,
                   aa.pet_id, p.pet_name, b.breed_name, s.shelter_name,
                   aa.application_date, aa.application_status, aa.reason_for_adoption,
                   NVL((SELECT MAX(home_status) FROM home_check hc WHERE hc.application_id=aa.application_id), 'Not Checked') AS home_status,
                   ar.adoption_id, ar.adoption_status, ar.adoption_date
            FROM adoption_application aa
            JOIN adopter a ON a.adopter_id = aa.adopter_id
            JOIN user_account u ON u.user_id = a.user_id
            JOIN pet p ON p.pet_id = aa.pet_id
            JOIN breed b ON b.breed_id = p.breed_id
            JOIN shelter s ON s.shelter_id = p.shelter_id
            LEFT JOIN adoption_record ar ON ar.application_id = aa.application_id
        """
        params: dict[str, Any] = {}
        if self.role() == "Adopter":
            sql += " WHERE aa.adopter_id = :adopter_id"
            params["adopter_id"] = self.user["adopter_id"]
        elif self.role() == "Shelter Staff":
            sql += " WHERE p.shelter_id = :shelter_id"
            params["shelter_id"] = self.user["staff_shelter_id"]
        sql += " ORDER BY aa.application_id DESC"
        return self.db.all(sql, params)

    def show_applications(self) -> None:
        self.clear_page()
        role = self.role()
        subtitle = "Manage adoption requests from submission to final adoption."
        if role == "Adopter":
            subtitle = "Your own adoption applications only. Other adopters' private data is hidden."
        self.page_header("Applications", subtitle)
        bar = self.toolbar()

        if role in ("Admin", "Shelter Staff"):
            self.add_action(bar, "Add Staff Document", self.add_document, COLORS["orange"])
            self.add_action(bar, "Add Home Check", self.add_home_check, COLORS["teal"])
            self.add_action(bar, "Recommend / Approve", self.approve_application, COLORS["green"])
            self.add_action(bar, "Reject Selected", self.reject_application, COLORS["rose"])
        if role == "Admin":
            self.add_action(bar, "Finalize Selected", self.finalize_adoption, COLORS["orange"])
        if role == "Adopter":
            self.add_action(bar, "Cancel Pending", self.cancel_application, COLORS["rose"])
        self.add_action(bar, "Refresh", self.show_applications, COLORS["blue"])

        rows = self.application_rows()
        if role == "Adopter":
            columns = ["application_id", "pet_name", "breed_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_id", "adoption_status"]
        else:
            columns = ["application_id", "adopter_name", "pet_name", "breed_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_id", "adoption_status"]
        self.render_table(rows, columns)


    def add_home_check(self) -> None:
        assert self.db is not None and self.user is not None
        row = self.selected_row()
        if not row:
            return
        staff_id = self.user.get("staff_id")
        staff_options: dict[str, Any] = {}
        fields: list[dict[str, Any]] = [
            {"key": "home_status", "label": "Home Status", "type": "combo", "values": ["Scheduled", "Passed", "Failed", "Revisit"], "default": "Passed"},
            {"key": "remarks", "label": "Remarks", "type": "textbox"},
        ]
        if self.role() == "Admin":
            staff = self.db.all(
                """
                SELECT ss.staff_id, ua.full_name, s.shelter_name
                FROM shelter_staff ss
                JOIN user_account ua ON ua.user_id = ss.user_id
                JOIN shelter s ON s.shelter_id = ss.shelter_id
                ORDER BY ua.full_name
                """
            )
            staff_options = {f"{r['staff_id']} - {r['full_name']} ({r['shelter_name']})": r["staff_id"] for r in staff}
            fields.insert(0, {"key": "staff", "label": "Staff Member", "type": "combo", "values": list(staff_options), "required": True})
        data = self.ask_form("Add Home Check", fields, width=680)
        if not data:
            return
        if staff_options:
            staff_id = staff_options[data["staff"]]
        if not staff_id:
            raise ValueError("A shelter staff profile is required for home check.")
        self.db.run(
            """
            INSERT INTO home_check(application_id, staff_id, check_date, home_status, remarks)
            VALUES(:application_id, :staff_id, SYSDATE, :home_status, :remarks)
            """,
            {"application_id": row["application_id"], "staff_id": staff_id, "home_status": data["home_status"], "remarks": data["remarks"]},
        )
        self.show_applications()

    def approve_application(self) -> None:
        assert self.db is not None and self.user is not None
        if self.role() not in ("Admin", "Shelter Staff"):
            messagebox.showwarning("Not allowed", "Only staff or admin can recommend/approve applications.", parent=self)
            return
        row = self.selected_row()
        if not row:
            return
        app_id = row["application_id"]
        if self.role() == "Shelter Staff":
            app = self.db.one(
                """
                SELECT p.shelter_id
                FROM adoption_application aa
                JOIN pet p ON p.pet_id=aa.pet_id
                WHERE aa.application_id=:application_id
                """,
                {"application_id": app_id},
            )
            if not app or app["shelter_id"] != self.user.get("staff_shelter_id"):
                messagebox.showerror("Not allowed", "You can approve only applications for your shelter.", parent=self)
                return
        docs_verified = self.db.scalar(
            "SELECT COUNT(*) FROM application_document WHERE application_id=:id AND verification_status='Verified'",
            {"id": app_id},
        )
        if not docs_verified:
            messagebox.showwarning("Documents required", "Staff must create and verify at least one application document before approval.", parent=self)
            return
        home_passed = self.db.scalar(
            "SELECT COUNT(*) FROM home_check WHERE application_id=:id AND home_status='Passed'",
            {"id": app_id},
        )
        if not home_passed:
            messagebox.showwarning("Home check required", "A passed home check is required before approval.", parent=self)
            return
        self.db.proc("pkg_adoption.approve_application", [app_id])
        messagebox.showinfo("Recommended", "Application has been approved/recommended and the pet is reserved for admin finalization.", parent=self)
        self.show_applications()


    def reject_application(self) -> None:
        assert self.db is not None
        row = self.selected_row()
        if not row:
            return
        data = self.ask_form("Reject Application", [{"key": "reason", "label": "Reason", "type": "textbox"}], width=620)
        if not data:
            return
        self.db.proc("pkg_adoption.reject_application", [row["application_id"], data.get("reason")])
        self.show_applications()

    def finalize_adoption(self) -> None:
        assert self.db is not None and self.user is not None
        if self.role() != "Admin":
            messagebox.showwarning("Admin only", "Only the administrator can finalize adoption and create payment records.", parent=self)
            return
        row = self.selected_row()
        if not row:
            return
        app_id = row["application_id"]
        checklist = self.db.one(
            """
            SELECT aa.application_status, p.pet_id, p.pet_name, p.health_status, p.availability_status,
                   (SELECT COUNT(*) FROM application_document doc WHERE doc.application_id=aa.application_id AND doc.verification_status='Verified') AS verified_docs,
                   (SELECT COUNT(*) FROM home_check hc WHERE hc.application_id=aa.application_id AND hc.home_status='Passed') AS passed_home_checks,
                   (SELECT COUNT(*) FROM medical_record mr WHERE mr.pet_id=p.pet_id) AS medical_records,
                   (SELECT COUNT(*) FROM vaccination_record vr WHERE vr.pet_id=p.pet_id) AS vaccination_records,
                   (SELECT COUNT(*) FROM adoption_record ar JOIN adoption_application aa2 ON aa2.application_id=ar.application_id WHERE aa2.pet_id=p.pet_id AND ar.adoption_status='Completed') AS completed_adoptions
            FROM adoption_application aa
            JOIN pet p ON p.pet_id=aa.pet_id
            WHERE aa.application_id=:application_id
            """,
            {"application_id": app_id},
        )
        if not checklist:
            messagebox.showerror("Invalid", "Application not found.", parent=self)
            return
        problems = []
        if checklist["application_status"] != "Approved":
            problems.append("Application must be approved/recommended first.")
        if int(checklist["verified_docs"] or 0) == 0:
            problems.append("At least one staff-created document must be verified.")
        if int(checklist["passed_home_checks"] or 0) == 0:
            problems.append("Home check must be passed.")
        if int(checklist["medical_records"] or 0) == 0:
            problems.append("Veterinarian medical record is required.")
        if int(checklist["vaccination_records"] or 0) == 0:
            problems.append("Vaccination record is required.")
        if checklist["health_status"] != "Healthy":
            problems.append("Pet health status must be Healthy.")
        if checklist["availability_status"] != "Reserved":
            problems.append("Pet must be Reserved before finalization.")
        if int(checklist["completed_adoptions"] or 0) > 0:
            problems.append("This pet already has a completed adoption.")
        if problems:
            messagebox.showwarning("Final checklist incomplete", "Cannot finalize adoption:\n\n" + "\n".join(f"• {p}" for p in problems), parent=self)
            return
        data = self.ask_form(
            "Finalize Adoption",
            [
                {"key": "amount", "label": "Payment Amount", "default": "0", "required": True},
                {"key": "payment_method", "label": "Payment Method", "type": "combo", "values": ["Cash", "Card", "Bank Transfer", "Online", "Waived"]},
                {"key": "agreement_signed", "label": "Agreement Signed", "type": "combo", "values": ["Y", "N"], "default": "Y"},
            ],
        )
        if not data:
            return
        self.db.proc("pkg_adoption.finalize_adoption", [app_id, as_float(data["amount"]), data["payment_method"], data["agreement_signed"]])
        messagebox.showinfo("Completed", "Adoption and payment record created successfully. Other pending applications for this pet were rejected.", parent=self)
        self.show_applications()


    def cancel_application(self) -> None:
        assert self.db is not None and self.user is not None
        row = self.selected_row()
        if not row:
            return
        if row["application_status"] != "Pending":
            messagebox.showwarning("Cannot cancel", "Only pending applications can be cancelled.", parent=self)
            return
        self.db.run(
            "UPDATE adoption_application SET application_status='Cancelled' WHERE application_id=:id AND adopter_id=:adopter_id",
            {"id": row["application_id"], "adopter_id": self.user["adopter_id"]},
        )
        self.show_applications()

    def show_home_checks(self) -> None:
        self.clear_page()
        assert self.db is not None and self.user is not None
        self.page_header("Home Checks", "Suitability verification records before adoption approval.")
        sql = """
            SELECT hc.home_check_id, hc.application_id, ua.full_name AS staff_name,
                   adopter_user.full_name AS adopter_name, p.pet_name, hc.check_date, hc.home_status, hc.remarks
            FROM home_check hc
            JOIN shelter_staff ss ON ss.staff_id = hc.staff_id
            JOIN user_account ua ON ua.user_id = ss.user_id
            JOIN adoption_application aa ON aa.application_id = hc.application_id
            JOIN adopter a ON a.adopter_id = aa.adopter_id
            JOIN user_account adopter_user ON adopter_user.user_id = a.user_id
            JOIN pet p ON p.pet_id = aa.pet_id
        """
        params: dict[str, Any] = {}
        if self.role() == "Adopter":
            sql += " WHERE aa.adopter_id=:adopter_id"
            params["adopter_id"] = self.user["adopter_id"]
        elif self.role() == "Shelter Staff":
            sql += " WHERE p.shelter_id=:shelter_id"
            params["shelter_id"] = self.user["staff_shelter_id"]
        sql += " ORDER BY hc.home_check_id DESC"
        rows = self.db.all(sql, params)
        if self.role() == "Adopter":
            self.render_table(rows, ["home_check_id", "application_id", "pet_name", "check_date", "home_status"])
        else:
            self.render_table(rows, ["home_check_id", "application_id", "staff_name", "adopter_name", "pet_name", "check_date", "home_status", "remarks"])


    def show_documents(self) -> None:
        self.clear_page()
        assert self.db is not None and self.user is not None
        if self.role() == "Adopter":
            self.page_header("My Document Status", "Documents are created and verified by shelter staff. You can only view your own document status.")
        else:
            self.page_header("Application Documents", "Staff-created adopter documents and verification status.")
        bar = self.toolbar()
        if self.role() in ("Admin", "Shelter Staff"):
            self.add_action(bar, "Add Staff Document", self.add_document, COLORS["orange"])
            self.add_action(bar, "Verify / Update Selected", self.verify_document, COLORS["green"])
        self.add_action(bar, "Refresh", self.show_documents, COLORS["blue"])

        sql = """
            SELECT doc.document_id, doc.application_id, adopter_user.full_name AS adopter_name,
                   p.pet_name, doc.document_type, doc.document_url, doc.upload_date, doc.verification_status
            FROM application_document doc
            JOIN adoption_application aa ON aa.application_id = doc.application_id
            JOIN adopter a ON a.adopter_id = aa.adopter_id
            JOIN user_account adopter_user ON adopter_user.user_id = a.user_id
            JOIN pet p ON p.pet_id = aa.pet_id
        """
        params: dict[str, Any] = {}
        if self.role() == "Adopter":
            sql += " WHERE aa.adopter_id = :adopter_id"
            params["adopter_id"] = self.user["adopter_id"]
        elif self.role() == "Shelter Staff":
            sql += " WHERE p.shelter_id = :shelter_id"
            params["shelter_id"] = self.user["staff_shelter_id"]
        sql += " ORDER BY doc.document_id DESC"
        rows = self.db.all(sql, params)
        if self.role() == "Adopter":
            self.render_table(rows, ["document_id", "application_id", "pet_name", "document_type", "upload_date", "verification_status"])
        else:
            self.render_table(rows, ["document_id", "application_id", "adopter_name", "pet_name", "document_type", "document_url", "upload_date", "verification_status"])


    def add_document(self) -> None:
        assert self.db is not None and self.user is not None
        if self.role() not in ("Admin", "Shelter Staff"):
            messagebox.showwarning("Not allowed", "Application documents are created by shelter staff or admin only.", parent=self)
            return
        fields = [
            {"key": "application_id", "label": "Application ID", "required": True},
            {"key": "document_type", "label": "Document Type", "type": "combo", "values": ["CNIC", "Proof of Address", "Residence Proof", "Consent Form", "Previous Pet Ownership Proof", "Other"], "default": "CNIC"},
            {"key": "document_url", "label": "Document Path or URL", "placeholder": "docs/cnic.pdf"},
            {"key": "verification_status", "label": "Verification Status", "type": "combo", "values": ["Pending", "Verified", "Rejected"], "default": "Pending"},
        ]
        data = self.ask_form("Add Staff-Created Application Document", fields)
        if not data:
            return
        app_id = as_int(data["application_id"])
        app = self.db.one(
            """
            SELECT aa.application_id, p.shelter_id
            FROM adoption_application aa
            JOIN pet p ON p.pet_id=aa.pet_id
            WHERE aa.application_id=:application_id
            """,
            {"application_id": app_id},
        )
        if not app:
            messagebox.showerror("Invalid application", "Application ID does not exist.", parent=self)
            return
        if self.role() == "Shelter Staff" and app["shelter_id"] != self.user.get("staff_shelter_id"):
            messagebox.showerror("Not allowed", "You can add documents only for applications in your shelter.", parent=self)
            return
        self.db.run(
            """
            INSERT INTO application_document(application_id, document_type, document_url, upload_date, verification_status)
            VALUES(:application_id, :document_type, :document_url, SYSDATE, :verification_status)
            """,
            {"application_id": app_id, "document_type": data["document_type"], "document_url": data["document_url"], "verification_status": data["verification_status"]},
        )
        self.show_documents()

    def verify_document(self) -> None:
        assert self.db is not None and self.user is not None
        if self.role() not in ("Admin", "Shelter Staff"):
            messagebox.showwarning("Not allowed", "Only staff or admin can verify documents.", parent=self)
            return
        row = self.selected_row()
        if not row:
            return
        if self.role() == "Shelter Staff":
            app = self.db.one(
                """
                SELECT p.shelter_id
                FROM application_document doc
                JOIN adoption_application aa ON aa.application_id=doc.application_id
                JOIN pet p ON p.pet_id=aa.pet_id
                WHERE doc.document_id=:document_id
                """,
                {"document_id": row["document_id"]},
            )
            if not app or app["shelter_id"] != self.user.get("staff_shelter_id"):
                messagebox.showerror("Not allowed", "You can verify documents only for your shelter.", parent=self)
                return
        data = self.ask_form(
            "Verify Document",
            [{"key": "verification_status", "label": "Verification Status", "type": "combo", "values": ["Pending", "Verified", "Rejected"], "default": row.get("verification_status") or "Pending"}],
        )
        if not data:
            return
        self.db.run(
            "UPDATE application_document SET verification_status=:status WHERE document_id=:document_id",
            {"status": data["verification_status"], "document_id": row["document_id"]},
        )
        self.show_documents()


    def show_adoptions(self) -> None:
        self.clear_page()
        assert self.db is not None and self.user is not None
        if self.role() == "Adopter":
            self.page_header("My Adoptions & Feedback", "Your completed adoption records only. Other adopters' details are hidden.")
        else:
            self.page_header("Adoptions", "Completed, returned, and cancelled adoption records with payment and feedback details.")
        bar = self.toolbar()
        if self.role() == "Adopter":
            self.add_action(bar, "Add / Update Feedback", self.add_feedback, COLORS["orange"])
        if self.role() in ("Admin", "Shelter Staff"):
            self.add_action(bar, "Mark Returned", self.mark_returned, COLORS["rose"])
        self.add_action(bar, "Refresh", self.show_adoptions, COLORS["blue"])
        sql = """
            SELECT ar.adoption_id, ar.application_id, adopter_user.full_name AS adopter_name,
                   p.pet_name, ar.adoption_date, ar.adoption_status, ar.agreement_signed,
                   pay.amount, pay.payment_method, pay.payment_status,
                   rf.rating, rf.comments, rf.feedback_date
            FROM adoption_record ar
            JOIN adoption_application aa ON aa.application_id = ar.application_id
            JOIN adopter a ON a.adopter_id = aa.adopter_id
            JOIN user_account adopter_user ON adopter_user.user_id = a.user_id
            JOIN pet p ON p.pet_id = aa.pet_id
            LEFT JOIN payment pay ON pay.adoption_id = ar.adoption_id
            LEFT JOIN review_feedback rf ON rf.adoption_id = ar.adoption_id
        """
        params: dict[str, Any] = {}
        if self.role() == "Adopter":
            sql += " WHERE aa.adopter_id = :adopter_id"
            params["adopter_id"] = self.user["adopter_id"]
        elif self.role() == "Shelter Staff":
            sql += " WHERE p.shelter_id = :shelter_id"
            params["shelter_id"] = self.user["staff_shelter_id"]
        sql += " ORDER BY ar.adoption_id DESC"
        rows = self.db.all(sql, params)
        if self.role() == "Adopter":
            columns = ["adoption_id", "application_id", "pet_name", "adoption_date", "adoption_status", "agreement_signed", "amount", "payment_method", "payment_status", "rating", "comments", "feedback_date"]
        else:
            columns = ["adoption_id", "application_id", "adopter_name", "pet_name", "adoption_date", "adoption_status", "agreement_signed", "amount", "payment_method", "payment_status", "rating", "comments", "feedback_date"]
        self.render_table(rows, columns)


    def add_feedback(self) -> None:
        assert self.db is not None
        row = self.selected_row()
        if not row:
            return
        data = self.ask_form(
            "Add / Update Feedback",
            [
                {"key": "rating", "label": "Rating", "type": "combo", "values": ["1", "2", "3", "4", "5"], "default": str(row.get("rating") or "5")},
                {"key": "comments", "label": "Comments", "type": "textbox", "default": row.get("comments") or ""},
            ],
        )
        if not data:
            return
        exists = self.db.scalar("SELECT COUNT(*) FROM review_feedback WHERE adoption_id=:adoption_id", {"adoption_id": row["adoption_id"]})
        if exists:
            self.db.run(
                "UPDATE review_feedback SET comments=:comments, rating=:rating, feedback_date=SYSDATE WHERE adoption_id=:adoption_id",
                {"comments": data["comments"], "rating": as_int(data["rating"], 5), "adoption_id": row["adoption_id"]},
            )
        else:
            self.db.run(
                "INSERT INTO review_feedback(adoption_id, comments, rating, feedback_date) VALUES(:adoption_id, :comments, :rating, SYSDATE)",
                {"adoption_id": row["adoption_id"], "comments": data["comments"], "rating": as_int(data["rating"], 5)},
            )
        self.show_adoptions()

    def mark_returned(self) -> None:
        assert self.db is not None
        row = self.selected_row()
        if not row:
            return
        if not messagebox.askyesno("Confirm", "Mark this adoption as returned and make the pet available again?", parent=self):
            return
        def work(cur: oracledb.Cursor) -> None:
            cur.execute("UPDATE adoption_record SET adoption_status='Returned' WHERE adoption_id=:adoption_id", {"adoption_id": row["adoption_id"]})
            cur.execute(
                """
                UPDATE pet SET availability_status='Available'
                WHERE pet_id = (SELECT pet_id FROM adoption_application WHERE application_id=:application_id)
                """,
                {"application_id": row["application_id"]},
            )
        self.db.transaction(work)
        self.show_adoptions()

    def show_payments(self) -> None:
        self.clear_page()
        assert self.db is not None and self.user is not None
        self.page_header("Payments", "Adoption payment records created during final adoption.")
        sql = """
            SELECT pay.payment_id, pay.adoption_id, adopter_user.full_name AS adopter_name,
                   p.pet_name, pay.amount, pay.payment_date, pay.payment_method, pay.payment_status
            FROM payment pay
            JOIN adoption_record ar ON ar.adoption_id = pay.adoption_id
            JOIN adoption_application aa ON aa.application_id = ar.application_id
            JOIN adopter a ON a.adopter_id = aa.adopter_id
            JOIN user_account adopter_user ON adopter_user.user_id = a.user_id
            JOIN pet p ON p.pet_id = aa.pet_id
        """
        params: dict[str, Any] = {}
        if self.role() == "Adopter":
            sql += " WHERE aa.adopter_id = :adopter_id"
            params["adopter_id"] = self.user["adopter_id"]
        elif self.role() == "Shelter Staff":
            sql += " WHERE p.shelter_id = :shelter_id"
            params["shelter_id"] = self.user["staff_shelter_id"]
        sql += " ORDER BY pay.payment_id DESC"
        rows = self.db.all(sql, params)
        if self.role() == "Adopter":
            self.render_table(rows, ["payment_id", "adoption_id", "pet_name", "amount", "payment_date", "payment_method", "payment_status"])
        else:
            self.render_table(rows, ["payment_id", "adoption_id", "adopter_name", "pet_name", "amount", "payment_date", "payment_method", "payment_status"])


    def show_medical(self) -> None:
        self.clear_page()
        assert self.db is not None
        self.page_header("Medical Records", "Veterinarian checkups, diagnosis, treatment, and notes.")
        bar = self.toolbar()
        if self.role() in ("Admin", "Veterinarian"):
            self.add_action(bar, "Add Medical Record", self.add_medical_record, COLORS["orange"])
        self.add_action(bar, "Refresh", self.show_medical, COLORS["blue"])
        rows = self.db.all(
            """
            SELECT mr.medical_record_id, p.pet_name, ua.full_name AS veterinarian,
                   mr.checkup_date, mr.diagnosis, mr.treatment, mr.health_notes
            FROM medical_record mr
            JOIN pet p ON p.pet_id = mr.pet_id
            JOIN veterinarian v ON v.vet_id = mr.vet_id
            JOIN user_account ua ON ua.user_id = v.user_id
            ORDER BY mr.medical_record_id DESC
            """
        )
        self.render_table(rows, ["medical_record_id", "pet_name", "veterinarian", "checkup_date", "diagnosis", "treatment", "health_notes"])

    def add_medical_record(self) -> None:
        assert self.db is not None and self.user is not None
        pets = self.db.all("SELECT pet_id, pet_name FROM pet ORDER BY pet_name")
        pet_opts = {f"{r['pet_id']} - {r['pet_name']}": r["pet_id"] for r in pets}
        vet_id = self.user.get("vet_id")
        vet_opts: dict[str, Any] = {}
        fields: list[dict[str, Any]] = [
            {"key": "pet", "label": "Pet", "type": "combo", "values": list(pet_opts), "required": True},
            {"key": "checkup_date", "label": "Checkup Date (YYYY-MM-DD)", "placeholder": "2026-06-01"},
            {"key": "diagnosis", "label": "Diagnosis", "type": "textbox"},
            {"key": "treatment", "label": "Treatment", "type": "textbox"},
            {"key": "health_notes", "label": "Health Notes", "type": "textbox"},
        ]
        if self.role() == "Admin":
            vets = self.db.all("SELECT v.vet_id, ua.full_name FROM veterinarian v JOIN user_account ua ON ua.user_id=v.user_id ORDER BY ua.full_name")
            vet_opts = {f"{r['vet_id']} - {r['full_name']}": r["vet_id"] for r in vets}
            fields.insert(1, {"key": "vet", "label": "Veterinarian", "type": "combo", "values": list(vet_opts), "required": True})
        data = self.ask_form("Add Medical Record", fields, width=700)
        if not data:
            return
        if vet_opts:
            vet_id = vet_opts[data["vet"]]
        if not vet_id:
            raise ValueError("A veterinarian profile is required.")
        self.db.run(
            f"""
            INSERT INTO medical_record(pet_id, vet_id, checkup_date, diagnosis, treatment, health_notes)
            VALUES(:pet_id, :vet_id, {sql_date('checkup_date')}, :diagnosis, :treatment, :health_notes)
            """,
            {"pet_id": pet_opts[data["pet"]], "vet_id": vet_id, "checkup_date": data["checkup_date"], "diagnosis": data["diagnosis"], "treatment": data["treatment"], "health_notes": data["health_notes"]},
        )
        self.show_medical()

    def show_vaccinations(self) -> None:
        self.clear_page()
        assert self.db is not None
        self.page_header("Vaccinations", "Pet vaccination history and next due dates.")
        bar = self.toolbar()
        if self.role() in ("Admin", "Veterinarian"):
            self.add_action(bar, "Add Vaccination", self.add_vaccination, COLORS["orange"])
        self.add_action(bar, "Refresh", self.show_vaccinations, COLORS["blue"])
        rows = self.db.all(
            """
            SELECT vr.vaccination_id, p.pet_name, ua.full_name AS veterinarian,
                   vr.vaccine_name, vr.vaccination_date, vr.next_due_date
            FROM vaccination_record vr
            JOIN pet p ON p.pet_id = vr.pet_id
            JOIN veterinarian v ON v.vet_id = vr.vet_id
            JOIN user_account ua ON ua.user_id = v.user_id
            ORDER BY vr.vaccination_id DESC
            """
        )
        self.render_table(rows, ["vaccination_id", "pet_name", "veterinarian", "vaccine_name", "vaccination_date", "next_due_date"])

    def add_vaccination(self) -> None:
        assert self.db is not None and self.user is not None
        pets = self.db.all("SELECT pet_id, pet_name FROM pet ORDER BY pet_name")
        pet_opts = {f"{r['pet_id']} - {r['pet_name']}": r["pet_id"] for r in pets}
        vet_id = self.user.get("vet_id")
        vet_opts: dict[str, Any] = {}
        fields: list[dict[str, Any]] = [
            {"key": "pet", "label": "Pet", "type": "combo", "values": list(pet_opts), "required": True},
            {"key": "vaccine_name", "label": "Vaccine Name", "required": True},
            {"key": "vaccination_date", "label": "Vaccination Date (YYYY-MM-DD)", "placeholder": "2026-06-01"},
            {"key": "next_due_date", "label": "Next Due Date (YYYY-MM-DD)", "placeholder": "2027-06-01"},
        ]
        if self.role() == "Admin":
            vets = self.db.all("SELECT v.vet_id, ua.full_name FROM veterinarian v JOIN user_account ua ON ua.user_id=v.user_id ORDER BY ua.full_name")
            vet_opts = {f"{r['vet_id']} - {r['full_name']}": r["vet_id"] for r in vets}
            fields.insert(1, {"key": "vet", "label": "Veterinarian", "type": "combo", "values": list(vet_opts), "required": True})
        data = self.ask_form("Add Vaccination", fields, width=650)
        if not data:
            return
        if vet_opts:
            vet_id = vet_opts[data["vet"]]
        if not vet_id:
            raise ValueError("A veterinarian profile is required.")
        self.db.run(
            f"""
            INSERT INTO vaccination_record(pet_id, vet_id, vaccine_name, vaccination_date, next_due_date)
            VALUES(:pet_id, :vet_id, :vaccine_name, {sql_date('vaccination_date')}, {sql_date('next_due_date')})
            """,
            {"pet_id": pet_opts[data["pet"]], "vet_id": vet_id, "vaccine_name": data["vaccine_name"], "vaccination_date": data["vaccination_date"], "next_due_date": data["next_due_date"]},
        )
        self.show_vaccinations()

    # ------------------------- donations -------------------------
    def show_donations(self) -> None:
        self.clear_page()
        assert self.db is not None
        self.page_header("Donations", "Track donors and shelter contributions.")
        bar = self.toolbar()
        self.add_action(bar, "Add Donation", self.add_donation, COLORS["orange"])
        self.add_action(bar, "Refresh", self.show_donations, COLORS["blue"])
        rows = self.db.all(
            """
            SELECT d.donation_id, dn.donor_name, dn.donor_contact, d.amount, d.donation_date, s.shelter_name
            FROM donation d
            JOIN donor dn ON dn.donor_id = d.donor_id
            JOIN shelter s ON s.shelter_id = d.shelter_id
            ORDER BY d.donation_id DESC
            """
        )
        self.render_table(rows, ["donation_id", "donor_name", "donor_contact", "amount", "donation_date", "shelter_name"])

    def add_donation(self) -> None:
        assert self.db is not None
        shelters = self.db.all("SELECT shelter_id, shelter_name FROM shelter ORDER BY shelter_id")
        shelter_opts = {f"{r['shelter_id']} - {r['shelter_name']}": r["shelter_id"] for r in shelters}
        data = self.ask_form(
            "Add Donation",
            [
                {"key": "donor_name", "label": "Donor Name", "required": True},
                {"key": "donor_contact", "label": "Donor Contact", "required": True},
                {"key": "amount", "label": "Amount", "required": True},
                {"key": "shelter", "label": "Shelter", "type": "combo", "values": list(shelter_opts), "required": True},
            ],
        )
        if not data:
            return

        def work(cur: oracledb.Cursor) -> None:
            cur.execute("SELECT donor_id FROM donor WHERE donor_contact=:contact", {"contact": data["donor_contact"]})
            found = cur.fetchone()
            if found:
                donor_id = found[0]
                cur.execute("UPDATE donor SET donor_name=:name WHERE donor_id=:id", {"name": data["donor_name"], "id": donor_id})
            else:
                donor_var = cur.var(oracledb.NUMBER)
                cur.execute(
                    "INSERT INTO donor(donor_name, donor_contact) VALUES(:name, :contact) RETURNING donor_id INTO :id",
                    {"name": data["donor_name"], "contact": data["donor_contact"], "id": donor_var},
                )
                donor_id = int(donor_var.getvalue()[0])
            cur.execute(
                "INSERT INTO donation(donor_id, amount, donation_date, shelter_id) VALUES(:donor_id, :amount, SYSDATE, :shelter_id)",
                {"donor_id": donor_id, "amount": as_float(data["amount"]), "shelter_id": shelter_opts[data["shelter"]]},
            )

        self.db.transaction(work)
        self.show_donations()

    # ------------------------- pet types and breeds -------------------------
    def show_pet_types(self) -> None:
        self.clear_page()
        assert self.db is not None
        self.page_header("Pet Types & Breeds", "Manage pet categories such as dogs, cats, rabbits, parrots, sparrows, fish, turtles, and other home-friendly pets.")
        bar = self.toolbar()
        if self.role() in ("Admin", "Shelter Staff"):
            self.add_action(bar, "Add Pet Type", self.add_pet_category, COLORS["orange"])
            self.add_action(bar, "Add Breed", self.add_breed, COLORS["teal"])
        self.add_action(bar, "Refresh", self.show_pet_types, COLORS["blue"])
        ctk.CTkLabel(self.page, text="Pet Categories", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
        categories = self.db.all("SELECT category_id, category_name, description FROM pet_category ORDER BY category_name")
        self.render_table(categories, ["category_id", "category_name", "description"], height=7)
        ctk.CTkLabel(self.page, text="Breeds / Species", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
        breeds = self.db.all(
            """
            SELECT b.breed_id, c.category_name, b.breed_name
            FROM breed b
            JOIN pet_category c ON c.category_id = b.category_id
            ORDER BY c.category_name, b.breed_name
            """
        )
        self.render_table(breeds, ["breed_id", "category_name", "breed_name"], height=10)

    def add_pet_category(self) -> None:
        assert self.db is not None
        data = self.ask_form(
            "Add Pet Type",
            [
                {"key": "category_name", "label": "Pet Type / Category", "required": True, "placeholder": "Parrot / Rabbit / Fish"},
                {"key": "description", "label": "Description", "type": "textbox"},
            ],
            width=650,
        )
        if not data:
            return
        self.db.run(
            "INSERT INTO pet_category(category_name, description) VALUES(:name, :description)",
            {"name": data["category_name"].strip(), "description": data["description"]},
        )
        self.show_pet_types()

    def add_breed(self) -> None:
        assert self.db is not None
        categories = self.db.all("SELECT category_id, category_name FROM pet_category ORDER BY category_name")
        category_opts = {f"{r['category_id']} - {r['category_name']}": r["category_id"] for r in categories}
        data = self.ask_form(
            "Add Breed / Species",
            [
                {"key": "category", "label": "Pet Type", "type": "combo", "values": list(category_opts), "required": True},
                {"key": "breed_name", "label": "Breed / Species Name", "required": True, "placeholder": "Budgerigar / Persian / Labrador"},
            ],
            width=650,
        )
        if not data:
            return
        self.db.run(
            "INSERT INTO breed(breed_name, category_id) VALUES(:breed_name, :category_id)",
            {"breed_name": data["breed_name"].strip(), "category_id": category_opts[data["category"]]},
        )
        self.show_pet_types()

    # ------------------------- users and shelters -------------------------
    def show_users(self) -> None:
        self.clear_page()
        assert self.db is not None
        self.page_header("Users", "One admin controls staff, veterinarian, and adopter accounts. Adopters may also self-register from the login page.")
        bar = self.toolbar()
        self.add_action(bar, "Add User", self.add_user, COLORS["orange"])
        self.add_action(bar, "Toggle Active/Inactive", self.toggle_user, COLORS["teal"])
        self.add_action(bar, "Refresh", self.show_users, COLORS["blue"])
        rows = self.db.all(
            """
            SELECT ua.user_id, ua.full_name, ua.email, ua.phone_no, ua.account_status, r.role_name,
                   a.adopter_id, ss.staff_id, v.vet_id
            FROM user_account ua
            JOIN role r ON r.role_id = ua.role_id
            LEFT JOIN adopter a ON a.user_id = ua.user_id
            LEFT JOIN shelter_staff ss ON ss.user_id = ua.user_id
            LEFT JOIN veterinarian v ON v.user_id = ua.user_id
            ORDER BY ua.user_id
            """
        )
        self.render_table(rows, ["user_id", "full_name", "email", "phone_no", "account_status", "role_name", "adopter_id", "staff_id", "vet_id"])

    def add_user(self) -> None:
        assert self.db is not None
        roles = self.db.all("SELECT role_id, role_name FROM role WHERE role_name <> 'Admin' ORDER BY role_name")
        shelters = self.db.all("SELECT shelter_id, shelter_name FROM shelter ORDER BY shelter_name")
        role_opts = {r["role_name"]: r["role_id"] for r in roles}
        shelter_opts = {f"{r['shelter_id']} - {r['shelter_name']}": r["shelter_id"] for r in shelters}
        data = self.ask_form(
            "Add User",
            [
                {"key": "full_name", "label": "Full Name", "required": True},
                {"key": "email", "label": "Email", "required": True},
                {"key": "password", "label": "Temporary Password", "type": "password", "required": True},
                {"key": "phone_no", "label": "Phone"},
                {"key": "role", "label": "Role", "type": "combo", "values": list(role_opts), "required": True},
                {"key": "occupation", "label": "Adopter Occupation"},
                {"key": "residence_type", "label": "Adopter Residence Type"},
                {"key": "has_other_pets", "label": "Adopter Has Other Pets", "type": "combo", "values": ["N", "Y"]},
                {"key": "shelter", "label": "Staff Shelter", "type": "combo", "values": list(shelter_opts)},
                {"key": "designation", "label": "Staff Designation"},
                {"key": "clinic_name", "label": "Vet Clinic"},
                {"key": "specialization", "label": "Vet Specialization"},
            ],
            width=720,
        )
        if not data:
            return
        role_name = data["role"]

        def work(cur: oracledb.Cursor) -> None:
            user_var = cur.var(oracledb.NUMBER)
            cur.execute(
                """
                INSERT INTO user_account(full_name, email, password_hash, phone_no, account_status, role_id)
                VALUES(:full_name, :email, :password_hash, :phone_no, 'Active', :role_id)
                RETURNING user_id INTO :user_id
                """,
                {"full_name": data["full_name"], "email": data["email"].lower(), "password_hash": sha256(data["password"]), "phone_no": data["phone_no"], "role_id": role_opts[role_name], "user_id": user_var},
            )
            user_id = int(user_var.getvalue()[0])
            if role_name == "Adopter":
                cur.execute(
                    """
                    INSERT INTO adopter(user_id, occupation, residence_type, has_other_pets, adopter_status)
                    VALUES(:user_id, :occupation, :residence_type, :has_other_pets, 'Verified')
                    """,
                    {"user_id": user_id, "occupation": data["occupation"], "residence_type": data["residence_type"], "has_other_pets": data["has_other_pets"] or "N"},
                )
            elif role_name == "Shelter Staff":
                if not data.get("shelter"):
                    raise ValueError("Shelter Staff requires Staff Shelter.")
                cur.execute(
                    """
                    INSERT INTO shelter_staff(user_id, shelter_id, designation, joining_date)
                    VALUES(:user_id, :shelter_id, :designation, SYSDATE)
                    """,
                    {"user_id": user_id, "shelter_id": shelter_opts[data["shelter"]], "designation": data["designation"]},
                )
            elif role_name == "Veterinarian":
                cur.execute(
                    "INSERT INTO veterinarian(user_id, clinic_name, specialization) VALUES(:user_id, :clinic_name, :specialization)",
                    {"user_id": user_id, "clinic_name": data["clinic_name"], "specialization": data["specialization"]},
                )

        self.db.transaction(work)
        self.show_users()

    def toggle_user(self) -> None:
        assert self.db is not None and self.user is not None
        row = self.selected_row()
        if not row:
            return
        if row["user_id"] == self.user["user_id"]:
            messagebox.showwarning("Blocked", "You cannot deactivate your own logged-in account.", parent=self)
            return
        new_status = "Inactive" if row["account_status"] == "Active" else "Active"
        self.db.run("UPDATE user_account SET account_status=:status WHERE user_id=:id", {"status": new_status, "id": row["user_id"]})
        self.show_users()

    def show_shelters(self) -> None:
        self.clear_page()
        assert self.db is not None
        self.page_header("Shelters", "Shelter profiles, locations, and capacity.")
        bar = self.toolbar()
        self.add_action(bar, "Add Shelter", self.add_shelter, COLORS["orange"])
        self.add_action(bar, "Refresh", self.show_shelters, COLORS["blue"])
        rows = self.db.all("SELECT shelter_id, shelter_name, location, contact_no, capacity FROM shelter ORDER BY shelter_id")
        self.render_table(rows, ["shelter_id", "shelter_name", "location", "contact_no", "capacity"])

    def add_shelter(self) -> None:
        assert self.db is not None
        data = self.ask_form(
            "Add Shelter",
            [
                {"key": "shelter_name", "label": "Shelter Name", "required": True},
                {"key": "location", "label": "Location", "required": True},
                {"key": "contact_no", "label": "Contact No"},
                {"key": "capacity", "label": "Capacity", "default": "0"},
            ],
        )
        if not data:
            return
        self.db.run(
            "INSERT INTO shelter(shelter_name, location, contact_no, capacity) VALUES(:name, :location, :contact, :capacity)",
            {"name": data["shelter_name"], "location": data["location"], "contact": data["contact_no"], "capacity": as_int(data["capacity"])},
        )
        self.show_shelters()

    # ------------------------- reports -------------------------
    def show_reports(self) -> None:
        self.clear_page()
        assert self.db is not None and self.user is not None
        if self.role() == "Adopter":
            self.page_header("My Summary", "Private summary of your own applications and adoptions.")
            rows = self.application_rows()
            self.render_table(rows, ["application_id", "pet_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_status"], height=12)
            return
        if self.role() == "Veterinarian":
            self.page_header("Health Reports", "Health and vaccination summary for veterinary review.")
            rows = self.db.all("SELECT * FROM vw_pet_health_summary ORDER BY pet_id")
            self.render_table(rows, ["pet_id", "pet_name", "health_status", "last_checkup", "last_vaccination", "next_vaccine_due"], height=12)
            return

        self.page_header("Reports", "Management summaries for presentation and checking.")
        row = ctk.CTkFrame(self.page, fg_color="transparent")
        row.pack(fill="x", padx=30, pady=(0, 22))
        if self.role() == "Shelter Staff":
            shelter_id = self.user.get("staff_shelter_id")
            report_specs = [
                ("Pets by Status", "SELECT availability_status AS label, COUNT(*) AS value FROM pet WHERE shelter_id=:shelter_id GROUP BY availability_status ORDER BY availability_status", {"shelter_id": shelter_id}),
                ("Applications by Status", """
                    SELECT aa.application_status AS label, COUNT(*) AS value
                    FROM adoption_application aa JOIN pet p ON p.pet_id=aa.pet_id
                    WHERE p.shelter_id=:shelter_id
                    GROUP BY aa.application_status ORDER BY aa.application_status
                """, {"shelter_id": shelter_id}),
                ("Donations by Shelter", "SELECT shelter_name AS label, 0 AS value FROM shelter WHERE shelter_id=:shelter_id", {"shelter_id": shelter_id}),
            ]
        else:
            report_specs = [
                ("Pets by Status", "SELECT availability_status AS label, COUNT(*) AS value FROM pet GROUP BY availability_status ORDER BY availability_status", {}),
                ("Applications by Status", "SELECT application_status AS label, COUNT(*) AS value FROM adoption_application GROUP BY application_status ORDER BY application_status", {}),
                ("Donations by Shelter", "SELECT s.shelter_name AS label, NVL(SUM(d.amount),0) AS value FROM shelter s LEFT JOIN donation d ON d.shelter_id=s.shelter_id GROUP BY s.shelter_name ORDER BY s.shelter_name", {}),
            ]
        for title, sql, params in report_specs:
            card = ctk.CTkFrame(row, fg_color=COLORS["panel"], corner_radius=26)
            card.pack(side="left", fill="x", expand=True, padx=(0, 14))
            ctk.CTkLabel(card, text=title, text_color=COLORS["dark"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=22, pady=(20, 8))
            for r in self.db.all(sql, params):
                ctk.CTkLabel(card, text=f"{display(r['label'])}: {display(r['value'])}", text_color=COLORS["muted"], font=("Segoe UI", 14)).pack(anchor="w", padx=22, pady=2)
            ctk.CTkLabel(card, text=" ").pack(pady=(0, 12))

        ctk.CTkLabel(self.page, text="Pet Health Summary", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
        rows = self.db.all("SELECT * FROM vw_pet_health_summary ORDER BY pet_id")
        self.render_table(rows, ["pet_id", "pet_name", "health_status", "last_checkup", "last_vaccination", "next_vaccine_due"], height=10)

# -----------------------------------------------------------------------------
# FINAL PRESENTATION PATCH: professional alignment, clickable pet profiles, CRUD
# -----------------------------------------------------------------------------

def _homepage_stat(self, parent, icon, label, value, color):
    card = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=26)
    card.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(card, text=icon, font=("Segoe UI", 34)).grid(row=0, column=0, rowspan=2, padx=(22, 12), pady=20, sticky="n")
    ctk.CTkLabel(card, text=display(value), text_color=color, font=("Segoe UI", 34, "bold")).grid(row=0, column=1, padx=(0, 18), pady=(18, 0), sticky="w")
    ctk.CTkLabel(card, text=label, text_color=COLORS["muted"], font=("Segoe UI", 16, "bold"), wraplength=240, justify="left").grid(row=1, column=1, padx=(0, 18), pady=(0, 18), sticky="w")
    return card


def _show_login_final(self):
    self.clear_window()
    self.configure(fg_color=COLORS["bg"])
    root = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
    root.pack(fill="both", expand=True)
    root.grid_columnconfigure(0, weight=1, minsize=620)
    root.grid_columnconfigure(1, weight=1, minsize=560)
    root.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(root, fg_color=COLORS["bg"], corner_radius=0)
    left.grid(row=0, column=0, sticky="nsew", padx=(54, 28), pady=48)
    left.grid_columnconfigure(0, weight=1)

    brand = ctk.CTkFrame(left, fg_color=COLORS["soft"], corner_radius=28)
    brand.grid(row=0, column=0, sticky="w", pady=(5, 26))
    ctk.CTkLabel(brand, text="🐾  Fur Ever Paws", text_color=COLORS["orange2"], font=("Segoe UI", 28, "bold"), padx=24, pady=12).pack()

    ctk.CTkLabel(left, text="Professional Pet\nAdoption Management", text_color=COLORS["dark"], font=("Segoe UI", 46, "bold"), justify="left", wraplength=630).grid(row=1, column=0, sticky="w")

    quote = ctk.CTkFrame(left, fg_color="#FFF0D8", corner_radius=30)
    quote.grid(row=2, column=0, sticky="ew", pady=(32, 26))
    ctk.CTkLabel(quote, text="“A safe adoption starts with good records, clear checks, and responsible care.”", text_color=COLORS["dark"], font=("Segoe UI", 23, "bold"), wraplength=560, justify="left").pack(anchor="w", padx=30, pady=(26, 8))
    ctk.CTkLabel(quote, text="Pets • Shelters • Health • Adoption Workflow", text_color=COLORS["teal2"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=30, pady=(0, 26))

    feature_row = ctk.CTkFrame(left, fg_color="transparent")
    feature_row.grid(row=3, column=0, sticky="ew")
    feature_row.grid_columnconfigure((0, 1), weight=1)
    for i, (icon, title, body) in enumerate([
        ("🐶", "Pet Profiles", "Pictures, breed, behavior, health, and adoption status."),
        ("📋", "Applications", "Controlled staff review, home check, and admin finalization."),
        ("🩺", "Medical Care", "Medical and vaccination records managed by veterinarians."),
        ("🔐", "Private Access", "Each role sees only its own allowed information."),
    ]):
        card = ctk.CTkFrame(feature_row, fg_color=COLORS["panel"], corner_radius=22, height=154)
        card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=icon, font=("Segoe UI", 30)).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(card, text=title, text_color=COLORS["dark"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=18)
        ctk.CTkLabel(card, text=body, text_color=COLORS["muted"], font=("Segoe UI", 13, "bold"), wraplength=255, justify="left").pack(anchor="w", padx=18, pady=(5, 12))

    right = ctk.CTkFrame(root, fg_color=COLORS["panel"], corner_radius=38)
    right.grid(row=0, column=1, sticky="nsew", padx=(28, 54), pady=64)
    right.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(right, text="Login", text_color=COLORS["dark"], font=("Segoe UI", 44, "bold")).grid(row=0, column=0, sticky="w", padx=52, pady=(88, 42))
    email = ctk.CTkEntry(right, placeholder_text="Email address", height=56, corner_radius=18, fg_color=COLORS["bg"], border_color=COLORS["line"], text_color=COLORS["dark"], font=("Segoe UI", 16))
    email.grid(row=1, column=0, sticky="ew", padx=52, pady=(0, 20))
    password = ctk.CTkEntry(right, placeholder_text="Password", show="•", height=56, corner_radius=18, fg_color=COLORS["bg"], border_color=COLORS["line"], text_color=COLORS["dark"], font=("Segoe UI", 16))
    password.grid(row=2, column=0, sticky="ew", padx=52, pady=(0, 28))

    def do_login():
        if not self.connect_db():
            return
        row = self.db.one(
            """
            SELECT u.user_id, u.full_name, u.email, u.password_hash, u.phone_no, u.account_status,
                   r.role_name,
                   a.adopter_id,
                   ss.staff_id, ss.shelter_id AS staff_shelter_id,
                   v.vet_id
            FROM user_account u
            JOIN role r ON r.role_id = u.role_id
            LEFT JOIN adopter a ON a.user_id = u.user_id
            LEFT JOIN shelter_staff ss ON ss.user_id = u.user_id
            LEFT JOIN veterinarian v ON v.user_id = u.user_id
            WHERE LOWER(u.email)=LOWER(:email) AND u.account_status='Active'
            """,
            {"email": email.get().strip()},
        )
        if not row or row["password_hash"] != sha256(password.get().strip()):
            messagebox.showerror("Login failed", "Invalid email or password.", parent=self)
            return
        self.user = row
        self.show_main()

    password.bind("<Return>", lambda _e: do_login())
    ctk.CTkButton(right, text="Login", height=56, corner_radius=18, fg_color=COLORS["orange"], hover_color=COLORS["orange2"], font=("Segoe UI", 17, "bold"), command=do_login).grid(row=3, column=0, sticky="ew", padx=52, pady=(0, 22))
    ctk.CTkButton(right, text="Create Adopter Account", height=48, corner_radius=16, fg_color=COLORS["teal"], hover_color=COLORS["teal2"], font=("Segoe UI", 15, "bold"), command=self.show_registration).grid(row=4, column=0, sticky="ew", padx=52, pady=(0, 16))
    ctk.CTkLabel(right, text="Staff and veterinarian accounts are created by the administrator.", text_color=COLORS["muted"], font=("Segoe UI", 14)).grid(row=5, column=0, sticky="w", padx=52)


def _show_home_final(self):
    self.clear_page()
    assert self.user is not None and self.db is not None
    role = self.role()
    self.page_header("Home", f"Welcome, {self.user['full_name']}. Your {self.user['role_name']} workspace is ready.")

    hero = ctk.CTkFrame(self.page, fg_color=COLORS["orange"], corner_radius=34)
    hero.pack(fill="x", padx=30, pady=(0, 22))
    ctk.CTkLabel(hero, text="Fur Ever Paws adoption workflow", text_color="#FFFFFF", font=("Segoe UI", 38, "bold")).pack(anchor="w", padx=34, pady=(28, 6))
    ctk.CTkLabel(hero, text="Browse pets, submit applications, complete staff and vet checks, then finalize adoption through admin approval.", text_color="#FFF7ED", font=("Segoe UI", 21, "bold"), wraplength=1060, justify="left").pack(anchor="w", padx=34, pady=(0, 28))

    if role == "Adopter":
        aid = self.user.get("adopter_id")
        specs = [
            ("🐶", "Available Pets", "SELECT COUNT(*) FROM pet WHERE availability_status='Available'", {}, COLORS["teal"]),
            ("📋", "My Applications", "SELECT COUNT(*) FROM adoption_application WHERE adopter_id=:id", {"id": aid}, COLORS["blue"]),
            ("✅", "My Adoptions", "SELECT COUNT(*) FROM adoption_record ar JOIN adoption_application aa ON aa.application_id=ar.application_id WHERE aa.adopter_id=:id AND ar.adoption_status='Completed'", {"id": aid}, COLORS["green"]),
            ("📄", "My Documents", "SELECT COUNT(*) FROM application_document d JOIN adoption_application aa ON aa.application_id=d.application_id WHERE aa.adopter_id=:id", {"id": aid}, COLORS["purple"]),
        ]
        flow_items = [("1", "Browse", "View pet profiles and choose an available pet."), ("2", "Apply", "Fill the application form only."), ("3", "Staff Review", "Staff creates documents and records home check."), ("4", "Vet Check", "Vet records health and vaccination status."), ("5", "Final Decision", "Admin finalizes successful adoption.")]
    elif role == "Shelter Staff":
        sid = self.user.get("staff_shelter_id")
        specs = [
            ("🐾", "Shelter Pets", "SELECT COUNT(*) FROM pet WHERE shelter_id=:sid", {"sid": sid}, COLORS["teal"]),
            ("📋", "Applications", "SELECT COUNT(*) FROM adoption_application aa JOIN pet p ON p.pet_id=aa.pet_id WHERE p.shelter_id=:sid", {"sid": sid}, COLORS["blue"]),
            ("🏠", "Home Checks", "SELECT COUNT(*) FROM home_check hc JOIN adoption_application aa ON aa.application_id=hc.application_id JOIN pet p ON p.pet_id=aa.pet_id WHERE p.shelter_id=:sid", {"sid": sid}, COLORS["green"]),
            ("📄", "Documents", "SELECT COUNT(*) FROM application_document d JOIN adoption_application aa ON aa.application_id=d.application_id JOIN pet p ON p.pet_id=aa.pet_id WHERE p.shelter_id=:sid", {"sid": sid}, COLORS["purple"]),
        ]
        flow_items = [("1", "Review", "Open applications for shelter pets."), ("2", "Document", "Create and verify application document."), ("3", "Home Check", "Add suitability check result."), ("4", "Recommend", "Approve/recommend and reserve pet."), ("5", "Admin", "Admin completes final adoption.")]
    elif role == "Veterinarian":
        specs = [("🐾", "Pets", "SELECT COUNT(*) FROM pet", {}, COLORS["teal"]), ("🩺", "Medical Records", "SELECT COUNT(*) FROM medical_record", {}, COLORS["blue"]), ("💉", "Vaccinations", "SELECT COUNT(*) FROM vaccination_record", {}, COLORS["green"]), ("⚠️", "Needs Care", "SELECT COUNT(*) FROM pet WHERE health_status IN ('Under Treatment','Vaccination Due','Critical')", {}, COLORS["rose"])]
        flow_items = [("1", "Pet Profile", "Open pet details and history."), ("2", "Medical", "Add/update medical records."), ("3", "Vaccines", "Add/update vaccination records."), ("4", "Health", "Update pet health status."), ("5", "Clearance", "Healthy pets continue adoption.")]
    else:
        specs = [("🐶", "Available Pets", "SELECT COUNT(*) FROM pet WHERE availability_status='Available'", {}, COLORS["teal"]), ("📋", "Applications", "SELECT COUNT(*) FROM adoption_application", {}, COLORS["blue"]), ("✅", "Completed Adoptions", "SELECT COUNT(*) FROM adoption_record WHERE adoption_status='Completed'", {}, COLORS["green"]), ("💝", "Donations", "SELECT NVL(SUM(amount),0) FROM donation", {}, COLORS["purple"])]
        flow_items = [("1", "Application", "Adopter submits application form."), ("2", "Staff Review", "Documents and home check are completed."), ("3", "Vet Check", "Medical and vaccine records are checked."), ("4", "Admin Checklist", "Admin reviews requirements."), ("5", "Finalize", "Adoption and payment are recorded.")]

    stats = ctk.CTkFrame(self.page, fg_color="transparent")
    stats.pack(fill="x", padx=30, pady=(0, 24))
    stats.grid_columnconfigure((0, 1, 2, 3), weight=1)
    for i, (icon, label, sql, params, color) in enumerate(specs):
        card = _homepage_stat(self, stats, icon, label, self.db.scalar(sql, params), color)
        card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 3 else 8))

    ctk.CTkLabel(self.page, text="Workflow", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
    flow = ctk.CTkFrame(self.page, fg_color=COLORS["panel"], corner_radius=28)
    flow.pack(fill="x", padx=30, pady=(0, 24))
    flow.grid_columnconfigure(tuple(range(5)), weight=1)
    for i, (n, title, text) in enumerate(flow_items):
        box = ctk.CTkFrame(flow, fg_color=COLORS["bg"], corner_radius=22, height=160)
        box.grid(row=0, column=i, sticky="nsew", padx=10, pady=16)
        box.grid_propagate(False)
        ctk.CTkLabel(box, text=n, fg_color=COLORS["soft"], text_color=COLORS["orange2"], corner_radius=20, width=46, height=46, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=18, pady=(15, 6))
        ctk.CTkLabel(box, text=title, text_color=COLORS["dark"], font=("Segoe UI", 18, "bold"), wraplength=190, justify="left").pack(anchor="w", padx=18)
        ctk.CTkLabel(box, text=text, text_color=COLORS["muted"], font=("Segoe UI", 14), wraplength=190, justify="left").pack(anchor="w", padx=18, pady=(4, 10))

    if role in ("Admin", "Shelter Staff"):
        ctk.CTkLabel(self.page, text="Recent Adoption Pipeline", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(2, 8))
        self.render_table(self.application_rows()[:8], ["application_id", "adopter_name", "pet_name", "shelter_name", "application_status", "home_status", "adoption_status"], height=9)
    elif role == "Adopter":
        ctk.CTkLabel(self.page, text="My Recent Applications", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(2, 8))
        self.render_table(self.application_rows()[:8], ["application_id", "pet_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_status"], height=9)
    else:
        ctk.CTkLabel(self.page, text="Pet Health Summary", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(2, 8))
        rows = self.db.all("SELECT * FROM vw_pet_health_summary ORDER BY pet_id")
        self.render_table(rows, ["pet_id", "pet_name", "health_status", "last_checkup", "last_vaccination", "next_vaccine_due"], height=9)


def _show_pets_final(self):
    self.clear_page()
    self.page_header("Pet Gallery", "Click a pet to open its full profile with behavior, breed, medical history, and vaccination details.")
    bar = self.toolbar()
    if self.role() in ("Admin", "Shelter Staff"):
        self.add_action(bar, "Add Pet", self.add_pet_dialog, COLORS["orange"])
        self.add_action(bar, "Update Pet Details", self.update_pet_details, COLORS["teal"])
        self.add_action(bar, "Update Status", self.update_pet_status, COLORS["purple"])
        self.add_action(bar, "Add Image", self.add_pet_image, COLORS["blue"])
        self.add_action(bar, "Delete Pet", self.delete_pet, COLORS["rose"])
    self.add_action(bar, "Refresh", self.show_pets, COLORS["blue"])
    rows = self.pet_rows()
    grid = ctk.CTkFrame(self.page, fg_color="transparent")
    grid.pack(fill="both", expand=True, padx=30, pady=(0, 28))
    grid.grid_columnconfigure((0, 1), weight=1)
    for i, pet in enumerate(rows):
        card = self.pet_card(grid, pet)
        card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=14, pady=14)


def _pet_card_final(self, parent, pet):
    card = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=28)
    img = self.make_image(pet.get("image_url"), pet.get("pet_name", "Pet"), pet.get("category_name", "Pet"), size=(445, 285))
    image_lbl = ctk.CTkLabel(card, image=img, text="", cursor="hand2")
    image_lbl.pack(fill="x", padx=16, pady=(16, 10))
    top = ctk.CTkFrame(card, fg_color="transparent")
    top.pack(fill="x", padx=20)
    name_lbl = ctk.CTkLabel(top, text=pet["pet_name"], text_color=COLORS["dark"], font=("Segoe UI", 27, "bold"), cursor="hand2")
    name_lbl.pack(side="left")
    status_color = COLORS["green"] if pet["availability_status"] == "Available" else COLORS["yellow"]
    ctk.CTkLabel(top, text=pet["availability_status"], fg_color=status_color, text_color="#FFFFFF", corner_radius=12, padx=12, pady=5, font=("Segoe UI", 12, "bold")).pack(side="right")
    detail = f"{pet['category_name']} • {pet['breed_name']} • {pet['gender']} • {display(pet['age'])} yrs"
    ctk.CTkLabel(card, text=detail, text_color=COLORS["muted"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(6, 2))
    ctk.CTkLabel(card, text=f"Shelter: {pet['shelter_name']}", text_color=COLORS["teal2"], font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(0, 8))
    desc = display(pet.get("description")) or "Ready for a loving home."
    ctk.CTkLabel(card, text=desc[:130] + ("..." if len(desc) > 130 else ""), text_color=COLORS["muted"], font=("Segoe UI", 14), wraplength=430, justify="left").pack(anchor="w", padx=20, pady=(0, 12))
    actions = ctk.CTkFrame(card, fg_color="transparent")
    actions.pack(fill="x", padx=20, pady=(0, 18))
    ctk.CTkButton(actions, text="View Full Profile", fg_color=COLORS["teal"], hover_color=COLORS["teal2"], corner_radius=16, command=lambda p=pet: self.show_pet_detail(p["pet_id"])).pack(side="left", fill="x", expand=True, padx=(0, 8))
    if self.role() == "Adopter" and pet["availability_status"] == "Available":
        ctk.CTkButton(actions, text="Apply", fg_color=COLORS["orange"], hover_color=COLORS["orange2"], corner_radius=16, command=lambda p=pet: self.apply_for_pet(p)).pack(side="left", fill="x", expand=True)
    else:
        ctk.CTkLabel(actions, text=f"Pet ID: {pet['pet_id']}", text_color=COLORS["muted"], font=("Segoe UI", 13, "bold")).pack(side="left", fill="x", expand=True)
    for widget in (card, image_lbl, name_lbl):
        widget.bind("<Button-1>", lambda _e, pid=pet["pet_id"]: self.show_pet_detail(pid))
    return card


def _show_pet_detail(self, pet_id):
    self.clear_page()
    assert self.db is not None
    pet = self.db.one(
        """
        SELECT p.pet_id, p.pet_name, p.age, p.gender, p.color, p.size_label, p.rescue_date,
               p.description, p.health_status, p.availability_status, p.shelter_id, p.breed_id,
               b.breed_name, c.category_name, s.shelter_name, s.location, s.contact_no,
               (SELECT image_url FROM pet_image pi WHERE pi.pet_id=p.pet_id AND ROWNUM=1) AS image_url
        FROM pet p
        JOIN breed b ON b.breed_id=p.breed_id
        JOIN pet_category c ON c.category_id=b.category_id
        JOIN shelter s ON s.shelter_id=p.shelter_id
        WHERE p.pet_id=:pet_id
        """,
        {"pet_id": pet_id},
    )
    if not pet:
        messagebox.showerror("Missing", "Pet not found.", parent=self)
        self.show_pets(); return
    self.page_header(pet["pet_name"], f"{pet['category_name']} • {pet['breed_name']} • {pet['shelter_name']}")
    top = ctk.CTkFrame(self.page, fg_color=COLORS["panel"], corner_radius=32)
    top.pack(fill="x", padx=30, pady=(0, 24))
    top.grid_columnconfigure(1, weight=1)
    img = self.make_image(pet.get("image_url"), pet.get("pet_name", "Pet"), pet.get("category_name", "Pet"), size=(520, 360))
    ctk.CTkLabel(top, image=img, text="").grid(row=0, column=0, rowspan=2, padx=24, pady=24, sticky="n")
    info = ctk.CTkFrame(top, fg_color="transparent")
    info.grid(row=0, column=1, sticky="nsew", padx=(0, 24), pady=24)
    ctk.CTkLabel(info, text="Pet Profile", text_color=COLORS["orange2"], font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ctk.CTkLabel(info, text=pet["pet_name"], text_color=COLORS["dark"], font=("Segoe UI", 40, "bold")).pack(anchor="w", pady=(4, 8))
    ctk.CTkLabel(info, text=display(pet.get("description")) or "No description available.", text_color=COLORS["muted"], font=("Segoe UI", 17), wraplength=700, justify="left").pack(anchor="w", pady=(0, 14))
    chips = ctk.CTkFrame(info, fg_color="transparent")
    chips.pack(fill="x", pady=(0, 12))
    for txt, color in [(f"Type: {pet['category_name']}", COLORS["teal"]), (f"Breed: {pet['breed_name']}", COLORS["blue"]), (f"Health: {pet['health_status']}", COLORS["green"] if pet['health_status']=='Healthy' else COLORS['rose']), (f"Status: {pet['availability_status']}", COLORS["orange"]), (f"Age: {display(pet['age'])} yrs", COLORS["purple"]), (f"Gender: {pet['gender']}", COLORS["yellow"])]:
        ctk.CTkLabel(chips, text=txt, fg_color=color, text_color="#FFFFFF", corner_radius=16, padx=12, pady=6, font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0, 8), pady=4)
    facts = f"Color: {display(pet.get('color')) or 'Not specified'}\nSize: {display(pet.get('size_label')) or 'Not specified'}\nRescue Date: {display(pet.get('rescue_date')) or 'Not recorded'}\nShelter: {pet['shelter_name']}\nLocation: {display(pet.get('location'))}\nContact: {display(pet.get('contact_no'))}"
    ctk.CTkLabel(info, text=facts, text_color=COLORS["dark"], font=("Segoe UI", 16), justify="left").pack(anchor="w", pady=(4, 16))
    btns = ctk.CTkFrame(info, fg_color="transparent")
    btns.pack(anchor="w")
    ctk.CTkButton(btns, text="Back to Gallery", fg_color=COLORS["muted"], hover_color="#4B5563", corner_radius=16, command=self.show_pets).pack(side="left", padx=(0, 10))
    if self.role() == "Adopter" and pet["availability_status"] == "Available":
        ctk.CTkButton(btns, text="Apply for Adoption", fg_color=COLORS["orange"], hover_color=COLORS["orange2"], corner_radius=16, command=lambda p=pet: self.apply_for_pet(p)).pack(side="left")

    med = self.db.all(
        """
        SELECT mr.medical_record_id, ua.full_name AS veterinarian, mr.checkup_date, mr.diagnosis, mr.treatment, mr.health_notes
        FROM medical_record mr JOIN veterinarian v ON v.vet_id=mr.vet_id JOIN user_account ua ON ua.user_id=v.user_id
        WHERE mr.pet_id=:pet_id ORDER BY mr.checkup_date DESC, mr.medical_record_id DESC
        """, {"pet_id": pet_id})
    vac = self.db.all(
        """
        SELECT vr.vaccination_id, ua.full_name AS veterinarian, vr.vaccine_name, vr.vaccination_date, vr.next_due_date
        FROM vaccination_record vr JOIN veterinarian v ON v.vet_id=vr.vet_id JOIN user_account ua ON ua.user_id=v.user_id
        WHERE vr.pet_id=:pet_id ORDER BY vr.vaccination_date DESC, vr.vaccination_id DESC
        """, {"pet_id": pet_id})
    ctk.CTkLabel(self.page, text="Medical History", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
    self.render_table(med, ["medical_record_id", "veterinarian", "checkup_date", "diagnosis", "treatment", "health_notes"], height=6)
    ctk.CTkLabel(self.page, text="Vaccination History", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
    self.render_table(vac, ["vaccination_id", "veterinarian", "vaccine_name", "vaccination_date", "next_due_date"], height=6)


def _update_pet_details(self):
    row = self.selected_row()
    if not row:
        return
    assert self.db is not None
    pet = self.db.one("SELECT * FROM pet WHERE pet_id=:id", {"id": row["pet_id"]})
    shelters = self.db.all("SELECT shelter_id, shelter_name FROM shelter ORDER BY shelter_id")
    breeds = self.db.all("SELECT b.breed_id, b.breed_name, c.category_name FROM breed b JOIN pet_category c ON c.category_id=b.category_id ORDER BY b.breed_id")
    shelter_opts = {f"{r['shelter_id']} - {r['shelter_name']}": r["shelter_id"] for r in shelters}
    breed_opts = {f"{r['breed_id']} - {r['category_name']} / {r['breed_name']}": r["breed_id"] for r in breeds}
    def default_from(opts, value):
        for k, v in opts.items():
            if v == value: return k
        return next(iter(opts)) if opts else ""
    data = self.ask_form("Update Pet Details", [
        {"key": "pet_name", "label": "Pet Name", "default": pet.get("pet_name")},
        {"key": "age", "label": "Age", "default": display(pet.get("age"))},
        {"key": "gender", "label": "Gender", "type": "combo", "values": ["Male", "Female", "Unknown"], "default": pet.get("gender")},
        {"key": "color", "label": "Color", "default": pet.get("color")},
        {"key": "size_label", "label": "Size", "type": "combo", "values": ["Small", "Medium", "Large"], "default": pet.get("size_label") or "Medium"},
        {"key": "rescue_date", "label": "Rescue Date (YYYY-MM-DD)", "default": display(pet.get("rescue_date"))},
        {"key": "shelter", "label": "Shelter", "type": "combo", "values": list(shelter_opts), "default": default_from(shelter_opts, pet.get("shelter_id"))},
        {"key": "breed", "label": "Pet Type / Breed", "type": "combo", "values": list(breed_opts), "default": default_from(breed_opts, pet.get("breed_id"))},
        {"key": "description", "label": "Description / Nature / Behavior", "type": "textbox", "default": pet.get("description") or ""},
    ], width=760)
    if not data: return
    self.db.run(f"""
        UPDATE pet SET pet_name=:pet_name, age=:age, gender=:gender, color=:color, size_label=:size_label,
        rescue_date={sql_date('rescue_date')}, shelter_id=:shelter_id, breed_id=:breed_id, description=:description
        WHERE pet_id=:pet_id
    """, {"pet_name": data["pet_name"], "age": as_float(data["age"]), "gender": data["gender"], "color": data["color"], "size_label": data["size_label"], "rescue_date": data["rescue_date"], "shelter_id": shelter_opts[data["shelter"]], "breed_id": breed_opts[data["breed"]], "description": data["description"], "pet_id": row["pet_id"]})
    messagebox.showinfo("Updated", "Pet information updated successfully.", parent=self)
    self.show_pets()


def _delete_pet(self):
    row = self.selected_row()
    if not row: return
    assert self.db is not None
    active = self.db.scalar("SELECT COUNT(*) FROM adoption_application WHERE pet_id=:id", {"id": row["pet_id"]})
    if active:
        messagebox.showwarning("Cannot delete", "This pet has adoption applications. Mark it Unavailable instead of deleting.", parent=self)
        return
    if not messagebox.askyesno("Confirm delete", f"Delete pet '{row['pet_name']}' permanently?", parent=self):
        return
    self.db.run("DELETE FROM pet WHERE pet_id=:id", {"id": row["pet_id"]})
    self.show_pets()


def _show_medical_final(self):
    self.clear_page(); assert self.db is not None
    self.page_header("Medical Records", "Veterinarian checkups, diagnosis, treatment, and notes.")
    bar = self.toolbar()
    if self.role() in ("Admin", "Veterinarian"):
        self.add_action(bar, "Add Medical Record", self.add_medical_record, COLORS["orange"])
        self.add_action(bar, "Update Selected", self.update_medical_record, COLORS["teal"])
        self.add_action(bar, "Delete Selected", self.delete_medical_record, COLORS["rose"])
    self.add_action(bar, "Refresh", self.show_medical, COLORS["blue"])
    rows = self.db.all("""
        SELECT mr.medical_record_id, mr.pet_id, p.pet_name, mr.vet_id, ua.full_name AS veterinarian, mr.checkup_date, mr.diagnosis, mr.treatment, mr.health_notes
        FROM medical_record mr JOIN pet p ON p.pet_id=mr.pet_id JOIN veterinarian v ON v.vet_id=mr.vet_id JOIN user_account ua ON ua.user_id=v.user_id
        ORDER BY mr.medical_record_id DESC
    """)
    self.render_table(rows, ["medical_record_id", "pet_id", "pet_name", "veterinarian", "checkup_date", "diagnosis", "treatment", "health_notes"])


def _update_medical_record(self):
    row = self.selected_row();
    if not row: return
    assert self.db is not None
    data = self.ask_form("Update Medical Record", [
        {"key": "checkup_date", "label": "Checkup Date (YYYY-MM-DD)", "default": display(row.get("checkup_date"))},
        {"key": "diagnosis", "label": "Diagnosis", "type": "textbox", "default": row.get("diagnosis") or ""},
        {"key": "treatment", "label": "Treatment", "type": "textbox", "default": row.get("treatment") or ""},
        {"key": "health_notes", "label": "Health Notes", "type": "textbox", "default": row.get("health_notes") or ""},
    ], width=700)
    if not data: return
    self.db.run(f"UPDATE medical_record SET checkup_date={sql_date('checkup_date')}, diagnosis=:diagnosis, treatment=:treatment, health_notes=:health_notes WHERE medical_record_id=:id", {"checkup_date": data["checkup_date"], "diagnosis": data["diagnosis"], "treatment": data["treatment"], "health_notes": data["health_notes"], "id": row["medical_record_id"]})
    self.show_medical()


def _delete_medical_record(self):
    row = self.selected_row()
    if not row: return
    if messagebox.askyesno("Confirm delete", "Delete selected medical record?", parent=self):
        self.db.run("DELETE FROM medical_record WHERE medical_record_id=:id", {"id": row["medical_record_id"]})
        self.show_medical()


def _show_vaccinations_final(self):
    self.clear_page(); assert self.db is not None
    self.page_header("Vaccinations", "Pet vaccination history and next due dates.")
    bar = self.toolbar()
    if self.role() in ("Admin", "Veterinarian"):
        self.add_action(bar, "Add Vaccination", self.add_vaccination, COLORS["orange"])
        self.add_action(bar, "Update Selected", self.update_vaccination, COLORS["teal"])
        self.add_action(bar, "Delete Selected", self.delete_vaccination, COLORS["rose"])
    self.add_action(bar, "Refresh", self.show_vaccinations, COLORS["blue"])
    rows = self.db.all("""
        SELECT vr.vaccination_id, vr.pet_id, p.pet_name, vr.vet_id, ua.full_name AS veterinarian, vr.vaccine_name, vr.vaccination_date, vr.next_due_date
        FROM vaccination_record vr JOIN pet p ON p.pet_id=vr.pet_id JOIN veterinarian v ON v.vet_id=vr.vet_id JOIN user_account ua ON ua.user_id=v.user_id
        ORDER BY vr.vaccination_id DESC
    """)
    self.render_table(rows, ["vaccination_id", "pet_id", "pet_name", "veterinarian", "vaccine_name", "vaccination_date", "next_due_date"])


def _update_vaccination(self):
    row = self.selected_row();
    if not row: return
    data = self.ask_form("Update Vaccination", [
        {"key": "vaccine_name", "label": "Vaccine Name", "default": row.get("vaccine_name")},
        {"key": "vaccination_date", "label": "Vaccination Date (YYYY-MM-DD)", "default": display(row.get("vaccination_date"))},
        {"key": "next_due_date", "label": "Next Due Date (YYYY-MM-DD)", "default": display(row.get("next_due_date"))},
    ], width=650)
    if not data: return
    self.db.run(f"UPDATE vaccination_record SET vaccine_name=:name, vaccination_date={sql_date('vaccination_date')}, next_due_date={sql_date('next_due_date')} WHERE vaccination_id=:id", {"name": data["vaccine_name"], "vaccination_date": data["vaccination_date"], "next_due_date": data["next_due_date"], "id": row["vaccination_id"]})
    self.show_vaccinations()


def _delete_vaccination(self):
    row = self.selected_row()
    if not row: return
    if messagebox.askyesno("Confirm delete", "Delete selected vaccination record?", parent=self):
        self.db.run("DELETE FROM vaccination_record WHERE vaccination_id=:id", {"id": row["vaccination_id"]})
        self.show_vaccinations()


def _create_verified_document(self):
    row = self.selected_row()
    if not row: return
    assert self.db is not None
    if self.role() not in ("Admin", "Shelter Staff"):
        return
    data = self.ask_form("Create Verified Staff Document", [
        {"key": "document_type", "label": "Document Type", "type": "combo", "values": ["CNIC", "Proof of Address", "Residence Proof", "Consent Form", "Staff Review Form", "Other"], "default": "Staff Review Form"},
        {"key": "document_url", "label": "Document Path / Note", "default": "Created and verified by shelter staff"},
    ], width=660)
    if not data: return
    self.db.run("INSERT INTO application_document(application_id, document_type, document_url, upload_date, verification_status) VALUES(:app, :type, :url, SYSDATE, 'Verified')", {"app": row["application_id"], "type": data["document_type"], "url": data["document_url"]})
    self.show_applications()


def _show_applications_final(self):
    self.clear_page()
    role = self.role()
    subtitle = "Your own adoption applications only." if role == "Adopter" else "Manage adoption requests with staff review, home checks, and admin finalization."
    self.page_header("Applications", subtitle)
    bar = self.toolbar()
    if role in ("Admin", "Shelter Staff"):
        self.add_action(bar, "Create Verified Document", self.create_verified_document, COLORS["orange"])
        self.add_action(bar, "Add Home Check", self.add_home_check, COLORS["teal"])
        self.add_action(bar, "Recommend / Approve", self.approve_application, COLORS["green"])
        self.add_action(bar, "Reject Selected", self.reject_application, COLORS["rose"])
    if role == "Admin":
        self.add_action(bar, "Finalize Selected", self.finalize_adoption, COLORS["orange"])
    if role == "Adopter":
        self.add_action(bar, "Cancel Pending", self.cancel_application, COLORS["rose"])
    self.add_action(bar, "Refresh", self.show_applications, COLORS["blue"])
    rows = self.application_rows()
    if role == "Adopter":
        cols = ["application_id", "pet_name", "breed_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_id", "adoption_status"]
    else:
        cols = ["application_id", "adopter_name", "pet_name", "breed_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_id", "adoption_status"]
    self.render_table(rows, cols)

# Install patched methods on the main class.
PremiumPetAdoptionApp.show_login = _show_login_final
PremiumPetAdoptionApp.show_home = _show_home_final
PremiumPetAdoptionApp.show_pets = _show_pets_final
PremiumPetAdoptionApp.pet_card = _pet_card_final
PremiumPetAdoptionApp.show_pet_detail = _show_pet_detail
PremiumPetAdoptionApp.update_pet_details = _update_pet_details
PremiumPetAdoptionApp.delete_pet = _delete_pet
PremiumPetAdoptionApp.show_medical = _show_medical_final
PremiumPetAdoptionApp.update_medical_record = _update_medical_record
PremiumPetAdoptionApp.delete_medical_record = _delete_medical_record
PremiumPetAdoptionApp.show_vaccinations = _show_vaccinations_final
PremiumPetAdoptionApp.update_vaccination = _update_vaccination
PremiumPetAdoptionApp.delete_vaccination = _delete_vaccination
PremiumPetAdoptionApp.create_verified_document = _create_verified_document
PremiumPetAdoptionApp.show_applications = _show_applications_final


# -----------------------------------------------------------------------------
# UI POLISH PATCH v8: aligned login, smooth dark sidebar, readable workflow
# -----------------------------------------------------------------------------
PRO = {
    "app_bg": "#F5F7FB",
    "card": "#FFFFFF",
    "nav": "#111827",
    "nav2": "#172033",
    "nav_hover": "#273247",
    "nav_text": "#F9FAFB",
    "nav_muted": "#CBD5E1",
    "accent": "#F97316",
    "accent2": "#EA580C",
    "teal": "#0F766E",
    "blue": "#2563EB",
    "green": "#16A34A",
    "purple": "#7C3AED",
    "rose": "#E11D48",
    "line": "#E5E7EB",
    "muted": "#64748B",
    "dark": "#14213D",
}


def _page_header_pro(self, title: str, subtitle: str = "") -> None:
    assert self.page is not None
    header = ctk.CTkFrame(self.page, fg_color=PRO["card"], corner_radius=24)
    header.pack(fill="x", padx=28, pady=(24, 18))
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(header, text=title, text_color=PRO["dark"], font=("Segoe UI", 34, "bold")).grid(
        row=0, column=0, sticky="w", padx=26, pady=(22, 4)
    )
    if subtitle:
        ctk.CTkLabel(header, text=subtitle, text_color=PRO["muted"], font=("Segoe UI", 16), wraplength=980, justify="left").grid(
            row=1, column=0, sticky="w", padx=26, pady=(0, 22)
        )


def _show_login_pro(self):
    self.clear_window()
    self.configure(fg_color=PRO["app_bg"])

    root = ctk.CTkFrame(self, fg_color=PRO["app_bg"], corner_radius=0)
    root.pack(fill="both", expand=True)
    root.grid_columnconfigure(0, weight=6, minsize=650)
    root.grid_columnconfigure(1, weight=5, minsize=540)
    root.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(root, fg_color="transparent", corner_radius=0)
    left.grid(row=0, column=0, sticky="nsew", padx=(54, 26), pady=42)
    left.grid_columnconfigure(0, weight=1)
    left.grid_rowconfigure(4, weight=1)

    brand = ctk.CTkFrame(left, fg_color="#FFF3E8", corner_radius=28)
    brand.grid(row=0, column=0, sticky="w", pady=(0, 24))
    ctk.CTkLabel(brand, text="🐾  Fur Ever Paws", text_color=PRO["accent2"], font=("Segoe UI", 29, "bold"), padx=26, pady=12).pack()

    ctk.CTkLabel(
        left,
        text="Pet Adoption\nManagement System",
        text_color=PRO["dark"],
        font=("Segoe UI", 46, "bold"),
        justify="left",
        wraplength=640,
    ).grid(row=1, column=0, sticky="w")

    ctk.CTkLabel(
        left,
        text="A complete desktop system for responsible pet adoption, shelter operations, health checks, payments, and reports.",
        text_color=PRO["muted"],
        font=("Segoe UI", 18, "bold"),
        justify="left",
        wraplength=640,
    ).grid(row=2, column=0, sticky="w", pady=(16, 24))

    quote = ctk.CTkFrame(left, fg_color=PRO["card"], corner_radius=28)
    quote.grid(row=3, column=0, sticky="ew", pady=(0, 22))
    ctk.CTkLabel(
        quote,
        text="“Every adoption deserves a safe home, a healthy pet, and a clear approval process.”",
        text_color=PRO["dark"],
        font=("Segoe UI", 22, "bold"),
        wraplength=585,
        justify="left",
    ).pack(anchor="w", padx=28, pady=(22, 6))
    ctk.CTkLabel(
        quote,
        text="Shelter records • Medical checks • Staff review • Final approval",
        text_color=PRO["teal"],
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w", padx=28, pady=(0, 22))

    feature_area = ctk.CTkFrame(left, fg_color="transparent")
    feature_area.grid(row=4, column=0, sticky="nsew")
    feature_area.grid_columnconfigure((0, 1), weight=1)
    feature_area.grid_rowconfigure((0, 1), weight=1)
    features = [
        ("🐶", "Pet Profiles", "Photos, breed, behavior, health, shelter, and adoption status."),
        ("📋", "Applications", "Structured application review with staff and admin control."),
        ("🩺", "Health Records", "Medical and vaccination records managed by veterinarians."),
        ("🔐", "Private Access", "Adopters only see their own applications and adoption records."),
    ]
    for i, (icon, title, body) in enumerate(features):
        card = ctk.CTkFrame(feature_area, fg_color=PRO["card"], corner_radius=22)
        card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(card, text=icon, font=("Segoe UI", 29)).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(card, text=title, text_color=PRO["dark"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20)
        ctk.CTkLabel(card, text=body, text_color=PRO["muted"], font=("Segoe UI", 13, "bold"), wraplength=255, justify="left").pack(anchor="w", padx=20, pady=(7, 18))

    right_shell = ctk.CTkFrame(root, fg_color="transparent", corner_radius=0)
    right_shell.grid(row=0, column=1, sticky="nsew", padx=(26, 54), pady=42)
    right_shell.grid_rowconfigure(0, weight=1)
    right_shell.grid_columnconfigure(0, weight=1)

    right = ctk.CTkFrame(right_shell, fg_color=PRO["card"], corner_radius=34)
    right.grid(row=0, column=0, sticky="nsew")
    right.grid_columnconfigure(0, weight=1)
    right.grid_rowconfigure(6, weight=1)

    ctk.CTkLabel(right, text="Secure Login", text_color=PRO["dark"], font=("Segoe UI", 39, "bold")).grid(row=0, column=0, sticky="w", padx=52, pady=(78, 10))
    ctk.CTkLabel(right, text="Enter your system account to continue.", text_color=PRO["muted"], font=("Segoe UI", 16, "bold")).grid(row=1, column=0, sticky="w", padx=52, pady=(0, 34))

    email = ctk.CTkEntry(right, placeholder_text="Email address", height=56, corner_radius=18, fg_color="#F8FAFC", border_color="#CBD5E1", text_color=PRO["dark"], font=("Segoe UI", 16))
    email.grid(row=2, column=0, sticky="ew", padx=52, pady=(0, 18))
    password = ctk.CTkEntry(right, placeholder_text="Password", show="•", height=56, corner_radius=18, fg_color="#F8FAFC", border_color="#CBD5E1", text_color=PRO["dark"], font=("Segoe UI", 16))
    password.grid(row=3, column=0, sticky="ew", padx=52, pady=(0, 28))

    def do_login():
        if not self.connect_db():
            return
        row = self.db.one(
            """
            SELECT u.user_id, u.full_name, u.email, u.password_hash, u.phone_no, u.account_status,
                   r.role_name,
                   a.adopter_id,
                   ss.staff_id, ss.shelter_id AS staff_shelter_id,
                   v.vet_id
            FROM user_account u
            JOIN role r ON r.role_id = u.role_id
            LEFT JOIN adopter a ON a.user_id = u.user_id
            LEFT JOIN shelter_staff ss ON ss.user_id = u.user_id
            LEFT JOIN veterinarian v ON v.user_id = u.user_id
            WHERE LOWER(u.email)=LOWER(:email) AND u.account_status='Active'
            """,
            {"email": email.get().strip()},
        )
        if not row or row["password_hash"] != sha256(password.get().strip()):
            messagebox.showerror("Login failed", "Invalid email or password.", parent=self)
            return
        self.user = row
        self.show_main()

    password.bind("<Return>", lambda _e: do_login())
    ctk.CTkButton(right, text="Login", height=56, corner_radius=18, fg_color=PRO["accent"], hover_color=PRO["accent2"], font=("Segoe UI", 17, "bold"), command=do_login).grid(row=4, column=0, sticky="ew", padx=52, pady=(0, 20))
    ctk.CTkButton(right, text="Create Adopter Account", height=50, corner_radius=16, fg_color=PRO["teal"], hover_color="#0B6B61", font=("Segoe UI", 15, "bold"), command=self.show_registration).grid(row=5, column=0, sticky="ew", padx=52, pady=(0, 18))
    ctk.CTkLabel(right, text="Staff and veterinarian accounts are created by the administrator.", text_color=PRO["muted"], font=("Segoe UI", 13, "bold"), wraplength=430, justify="left").grid(row=6, column=0, sticky="nw", padx=52, pady=(0, 30))


def _show_main_pro(self) -> None:
    self.clear_window()
    self.configure(fg_color=PRO["app_bg"])

    self.sidebar = ctk.CTkFrame(self, width=305, fg_color=PRO["nav"], corner_radius=0)
    self.sidebar.pack(side="left", fill="y")
    self.sidebar.pack_propagate(False)

    brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
    brand.pack(fill="x", padx=22, pady=(24, 12))
    ctk.CTkLabel(brand, text="🐾 Fur Ever Paws", text_color="#FFFFFF", font=("Segoe UI", 28, "bold")).pack(anchor="w")
    ctk.CTkLabel(brand, text="Management Console", text_color=PRO["nav_muted"], font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(3, 0))

    assert self.user is not None
    profile = ctk.CTkFrame(self.sidebar, fg_color=PRO["nav2"], corner_radius=22)
    profile.pack(fill="x", padx=18, pady=(0, 14))
    ctk.CTkLabel(profile, text=self.user["full_name"], text_color="#FFFFFF", font=("Segoe UI", 16, "bold"), wraplength=240, justify="left").pack(anchor="w", padx=18, pady=(16, 2))
    ctk.CTkLabel(profile, text=self.user["role_name"], text_color="#FDBA74", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(0, 16))

    ctk.CTkLabel(self.sidebar, text="NAVIGATION", text_color=PRO["nav_muted"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=24, pady=(0, 6))
    self.nav_area = ctk.CTkScrollableFrame(
        self.sidebar,
        fg_color="transparent",
        corner_radius=0,
        scrollbar_button_color="#334155",
        scrollbar_button_hover_color="#475569",
    )
    self.nav_area.pack(fill="both", expand=True, padx=0, pady=(0, 10))

    self.nav("🏡  Home", self.show_home)
    if self.role() == "Admin":
        items = [("🐾  Pet Gallery", self.show_pets), ("➕  Add Pet", self.add_pet_dialog), ("🧬  Pet Types & Breeds", self.show_pet_types), ("📋  Applications", self.show_applications), ("🏠  Home Checks", self.show_home_checks), ("✅  Adoptions", self.show_adoptions), ("📄  Documents", self.show_documents), ("💳  Payments", self.show_payments), ("💝  Donations", self.show_donations), ("🩺  Medical", self.show_medical), ("💉  Vaccinations", self.show_vaccinations), ("👥  Users", self.show_users), ("🏢  Shelters", self.show_shelters), ("📊  Reports", self.show_reports)]
    elif self.role() == "Shelter Staff":
        items = [("🐾  Pet Gallery", self.show_pets), ("➕  Add Pet", self.add_pet_dialog), ("🧬  Pet Types & Breeds", self.show_pet_types), ("📋  Applications", self.show_applications), ("🏠  Home Checks", self.show_home_checks), ("✅  Adoptions", self.show_adoptions), ("📄  Documents", self.show_documents), ("💳  Payments", self.show_payments), ("💝  Donations", self.show_donations), ("📊  Reports", self.show_reports)]
    elif self.role() == "Veterinarian":
        items = [("🐾  Pet Gallery", self.show_pets), ("🩺  Medical", self.show_medical), ("💉  Vaccinations", self.show_vaccinations), ("📊  Health Reports", self.show_reports)]
    else:
        items = [("🐾  Pet Gallery", self.show_pets), ("📋  My Applications", self.show_applications), ("📄  My Document Status", self.show_documents), ("✅  My Adoptions & Feedback", self.show_adoptions)]
    for label, cmd in items:
        self.nav(label, cmd)

    footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
    footer.pack(fill="x", padx=18, pady=(0, 18))
    ctk.CTkButton(footer, text="Logout", height=46, corner_radius=16, fg_color="#DC2626", hover_color="#B91C1C", font=("Segoe UI", 15, "bold"), command=self.show_login).pack(fill="x")

    self.page = ctk.CTkScrollableFrame(
        self,
        fg_color=PRO["app_bg"],
        corner_radius=0,
        scrollbar_button_color="#CBD5E1",
        scrollbar_button_hover_color="#94A3B8",
    )
    self.page.pack(side="right", fill="both", expand=True)
    self.show_home()


def _nav_pro(self, text: str, command: Callable[[], None]) -> None:
    assert self.nav_area is not None
    ctk.CTkButton(
        self.nav_area,
        text=text,
        anchor="w",
        height=46,
        corner_radius=14,
        fg_color="transparent",
        hover_color=PRO["nav_hover"],
        text_color=PRO["nav_text"],
        font=("Segoe UI", 14, "bold"),
        command=lambda: self.safe(command),
    ).pack(fill="x", padx=14, pady=4)


def _show_home_pro(self):
    self.clear_page()
    assert self.user is not None and self.db is not None
    role = self.role()
    self.page_header("Dashboard", f"Welcome, {self.user['full_name']}. This workspace shows the actions and records available for your role.")

    hero = ctk.CTkFrame(self.page, fg_color=PRO["dark"], corner_radius=28)
    hero.pack(fill="x", padx=28, pady=(0, 20))
    ctk.CTkLabel(hero, text="Fur Ever Paws Adoption Workflow", text_color="#FFFFFF", font=("Segoe UI", 31, "bold")).pack(anchor="w", padx=28, pady=(24, 6))
    ctk.CTkLabel(hero, text="A controlled process from pet browsing to final adoption, with separate responsibilities for adopters, staff, veterinarians, and admin.", text_color="#CBD5E1", font=("Segoe UI", 16, "bold"), wraplength=1050, justify="left").pack(anchor="w", padx=28, pady=(0, 24))

    if role == "Adopter":
        aid = self.user.get("adopter_id")
        specs = [("🐶", "Available Pets", "SELECT COUNT(*) FROM pet WHERE availability_status='Available'", {}, PRO["teal"]), ("📋", "My Applications", "SELECT COUNT(*) FROM adoption_application WHERE adopter_id=:id", {"id": aid}, PRO["blue"]), ("✅", "My Adoptions", "SELECT COUNT(*) FROM adoption_record ar JOIN adoption_application aa ON aa.application_id=ar.application_id WHERE aa.adopter_id=:id AND ar.adoption_status='Completed'", {"id": aid}, PRO["green"]), ("📄", "My Documents", "SELECT COUNT(*) FROM application_document d JOIN adoption_application aa ON aa.application_id=d.application_id WHERE aa.adopter_id=:id", {"id": aid}, PRO["purple"])]
        flow_items = [("Browse", "Open pet profiles and read complete pet details."), ("Apply", "Fill the adoption application form only."), ("Staff Review", "Staff prepares documents and records home check."), ("Veterinary Check", "Doctor updates medical and vaccination status."), ("Final Decision", "Admin finalizes successful adoption and payment.")]
    elif role == "Shelter Staff":
        sid = self.user.get("staff_shelter_id")
        specs = [("🐾", "Shelter Pets", "SELECT COUNT(*) FROM pet WHERE shelter_id=:sid", {"sid": sid}, PRO["teal"]), ("📋", "Applications", "SELECT COUNT(*) FROM adoption_application aa JOIN pet p ON p.pet_id=aa.pet_id WHERE p.shelter_id=:sid", {"sid": sid}, PRO["blue"]), ("🏠", "Home Checks", "SELECT COUNT(*) FROM home_check hc JOIN adoption_application aa ON aa.application_id=hc.application_id JOIN pet p ON p.pet_id=aa.pet_id WHERE p.shelter_id=:sid", {"sid": sid}, PRO["green"]), ("📄", "Documents", "SELECT COUNT(*) FROM application_document d JOIN adoption_application aa ON aa.application_id=d.application_id JOIN pet p ON p.pet_id=aa.pet_id WHERE p.shelter_id=:sid", {"sid": sid}, PRO["purple"])]
        flow_items = [("Review", "Review applications for pets in your shelter."), ("Documents", "Create and verify the staff-side application document."), ("Home Check", "Record whether the adopter's home is suitable."), ("Recommend", "Approve/recommend the case for admin review."), ("Admin Finalization", "Admin completes adoption and payment.")]
    elif role == "Veterinarian":
        specs = [("🐾", "Total Pets", "SELECT COUNT(*) FROM pet", {}, PRO["teal"]), ("🩺", "Medical Records", "SELECT COUNT(*) FROM medical_record", {}, PRO["blue"]), ("💉", "Vaccinations", "SELECT COUNT(*) FROM vaccination_record", {}, PRO["green"]), ("⚠️", "Needs Care", "SELECT COUNT(*) FROM pet WHERE health_status IN ('Under Treatment','Vaccination Due','Critical')", {}, PRO["rose"])]
        flow_items = [("Pet Review", "Open pet records that need medical attention."), ("Medical Record", "Add diagnosis, treatment, and notes."), ("Vaccination", "Record vaccine name and next due date."), ("Health Status", "Update pet health status."), ("Clearance", "Healthy pets can proceed in adoption workflow.")]
    else:
        specs = [("🐶", "Available Pets", "SELECT COUNT(*) FROM pet WHERE availability_status='Available'", {}, PRO["teal"]), ("📋", "Applications", "SELECT COUNT(*) FROM adoption_application", {}, PRO["blue"]), ("🏠", "Completed Adoptions", "SELECT COUNT(*) FROM adoption_record WHERE adoption_status='Completed'", {}, PRO["green"]), ("💝", "Donations", "SELECT NVL(SUM(amount),0) FROM donation", {}, PRO["purple"])]
        flow_items = [("Application", "Adopter submits application form."), ("Staff Review", "Staff creates documents and performs home check."), ("Vet Check", "Doctor confirms health and vaccination records."), ("Admin Approval", "Admin verifies all checks and finalizes adoption."), ("Payment & Feedback", "Payment is recorded and adopter can submit feedback.")]

    stats = ctk.CTkFrame(self.page, fg_color="transparent")
    stats.pack(fill="x", padx=28, pady=(0, 22))
    stats.grid_columnconfigure((0, 1, 2, 3), weight=1)
    for i, (icon, label, sql, params, color) in enumerate(specs):
        value = self.db.scalar(sql, params)
        card = ctk.CTkFrame(stats, fg_color=PRO["card"], corner_radius=22)
        card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
        ctk.CTkLabel(card, text=icon, font=("Segoe UI", 30)).pack(anchor="w", padx=22, pady=(18, 0))
        ctk.CTkLabel(card, text=display(value), text_color=color, font=("Segoe UI", 33, "bold")).pack(anchor="w", padx=22)
        ctk.CTkLabel(card, text=label, text_color=PRO["muted"], font=("Segoe UI", 14, "bold"), wraplength=180, justify="left").pack(anchor="w", padx=22, pady=(0, 18))

    workflow = ctk.CTkFrame(self.page, fg_color=PRO["card"], corner_radius=26)
    workflow.pack(fill="x", padx=28, pady=(0, 22))
    ctk.CTkLabel(workflow, text="Workflow", text_color=PRO["dark"], font=("Segoe UI", 27, "bold")).pack(anchor="w", padx=26, pady=(22, 8))
    for idx, (title, body) in enumerate(flow_items, start=1):
        row = ctk.CTkFrame(workflow, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(3, 7))
        ctk.CTkLabel(row, text=str(idx), fg_color="#FFF3E8", text_color=PRO["accent2"], corner_radius=18, width=42, height=42, font=("Segoe UI", 17, "bold")).pack(side="left", padx=(0, 14))
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_col, text=title, text_color=PRO["dark"], font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ctk.CTkLabel(text_col, text=body, text_color=PRO["muted"], font=("Segoe UI", 14), wraplength=900, justify="left").pack(anchor="w", pady=(2, 0))
    ctk.CTkLabel(workflow, text=" ").pack(pady=(0, 6))

    if role in ("Admin", "Shelter Staff"):
        ctk.CTkLabel(self.page, text="Recent Adoption Pipeline", text_color=PRO["dark"], font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
        rows = self.application_rows()[:8]
        self.render_table(rows, ["application_id", "adopter_name", "pet_name", "shelter_name", "application_status", "home_status", "adoption_status"], height=8)
    elif role == "Adopter":
        ctk.CTkLabel(self.page, text="My Recent Applications", text_color=PRO["dark"], font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
        rows = self.application_rows()[:8]
        self.render_table(rows, ["application_id", "pet_name", "shelter_name", "application_date", "application_status", "home_status", "adoption_status"], height=8)
    elif role == "Veterinarian":
        ctk.CTkLabel(self.page, text="Pet Health Summary", text_color=PRO["dark"], font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=30, pady=(4, 8))
        rows = self.db.all("SELECT * FROM vw_pet_health_summary ORDER BY pet_id")
        self.render_table(rows, ["pet_id", "pet_name", "health_status", "last_checkup", "last_vaccination", "next_vaccine_due"], height=8)


# Apply UI polish overrides.
PremiumPetAdoptionApp.page_header = _page_header_pro
PremiumPetAdoptionApp.show_login = _show_login_pro
PremiumPetAdoptionApp.show_main = _show_main_pro
PremiumPetAdoptionApp.nav = _nav_pro
PremiumPetAdoptionApp.show_home = _show_home_pro


# -----------------------------------------------------------------------------
# v10 PET PROFILE + SCROLL FIX OVERRIDES
# -----------------------------------------------------------------------------

def _reset_scroll_to_top(self) -> None:
    """Reset CTkScrollableFrame position so page changes never open blank."""
    try:
        if self.page is not None and hasattr(self.page, "_parent_canvas"):
            self.page._parent_canvas.yview_moveto(0)
    except Exception:
        pass


def _clear_page_v10(self) -> None:
    if self.page is None:
        return
    for widget in self.page.winfo_children():
        widget.destroy()
    self.active_rows = []
    self.active_tree = None
    try:
        self.after(10, lambda: _reset_scroll_to_top(self))
    except Exception:
        pass


PET_GUIDES = {
    "Dog": {
        "lifespan": "10–13 years",
        "temperament": "Loyal, social, trainable, and family-focused.",
        "care": "Needs daily walks, routine grooming, training, and social time.",
        "environment": "Best for homes where someone can give regular attention and exercise.",
        "diet": "Balanced dog food, clean water, and controlled treats.",
        "activity": "Medium to high activity depending on breed and age.",
    },
    "Cat": {
        "lifespan": "12–18 years",
        "temperament": "Independent, affectionate, curious, and calm when comfortable.",
        "care": "Needs a clean litter area, scratching post, grooming, and indoor enrichment.",
        "environment": "Best for apartments or homes with safe indoor space.",
        "diet": "Balanced cat food, clean water, and age-appropriate feeding.",
        "activity": "Moderate activity with short play sessions and climbing spaces.",
    },
    "Rabbit": {
        "lifespan": "8–12 years",
        "temperament": "Gentle, quiet, sensitive, and social with careful handling.",
        "care": "Needs hay, safe chewing toys, a clean enclosure, and calm handling.",
        "environment": "Best for peaceful homes with supervised indoor space.",
        "diet": "Hay, leafy greens, pellets in moderation, and fresh water.",
        "activity": "Needs daily safe movement outside the cage/enclosure.",
    },
    "Bird": {
        "lifespan": "5–20 years depending on species",
        "temperament": "Alert, social, vocal, and intelligent.",
        "care": "Needs a clean cage, safe perches, enrichment, and regular interaction.",
        "environment": "Best for homes that can handle sound and daily care.",
        "diet": "Species-appropriate seed/pellet mix, fruits/vegetables where suitable, and water.",
        "activity": "Needs mental stimulation and supervised movement when possible.",
    },
    "Fish": {
        "lifespan": "5–10 years depending on species and water quality",
        "temperament": "Calm, low-contact, and environment-sensitive.",
        "care": "Needs proper tank size, filtration, water changes, and stable temperature.",
        "environment": "Best for adopters who can maintain aquarium conditions.",
        "diet": "Aquarium fish food in controlled quantity.",
        "activity": "Low handling; focus is on clean habitat and feeding routine.",
    },
    "Turtle": {
        "lifespan": "20–40 years",
        "temperament": "Calm, slow-moving, and long-term care dependent.",
        "care": "Needs proper tank, basking area, UV light, clean water, and careful hygiene.",
        "environment": "Best for adopters prepared for long-term care.",
        "diet": "Species-appropriate pellets, vegetables, and occasional protein if suitable.",
        "activity": "Low activity but needs correct habitat setup.",
    },
    "Hamster": {
        "lifespan": "2–3 years",
        "temperament": "Small, active, curious, and mostly evening/night active.",
        "care": "Needs clean bedding, exercise wheel, hideouts, and careful handling.",
        "environment": "Best for quiet homes and gentle handling.",
        "diet": "Hamster mix, small safe vegetables, and clean water.",
        "activity": "High activity in short bursts, especially at night.",
    },
    "Guinea Pig": {
        "lifespan": "5–8 years",
        "temperament": "Gentle, vocal, social, and friendly with patience.",
        "care": "Needs space, hay, vitamin C, clean bedding, and companionship.",
        "environment": "Best for calm indoor homes with enough enclosure space.",
        "diet": "Hay, pellets, vitamin-C rich vegetables, and clean water.",
        "activity": "Needs daily supervised floor time and social interaction.",
    },
}

BREED_NOTES = {
    "Labrador Mix": "Usually friendly, active, trainable, and good for families.",
    "German Shepherd": "Intelligent, loyal, protective, and needs structured training.",
    "Golden Retriever": "Gentle, affectionate, playful, and usually excellent with families.",
    "Beagle": "Curious, energetic, scent-driven, and needs regular walks.",
    "Persian": "Calm, quiet, affectionate, and needs regular coat grooming.",
    "Siamese": "Social, vocal, intelligent, and enjoys human interaction.",
    "Local Shorthair": "Adaptable, playful, low-maintenance, and affectionate.",
    "Maine Coon": "Large, confident, gentle, and usually sociable.",
    "Dutch Rabbit": "Small, calm, friendly, and good for quiet homes.",
    "Holland Lop": "Gentle, compact, affectionate, and needs careful handling.",
    "Parrot": "Highly intelligent, social, vocal, and needs daily enrichment.",
    "Budgerigar": "Cheerful, active, social, and suitable for attentive beginners.",
    "Goldfish": "Peaceful aquarium pet that depends heavily on water quality.",
    "Red-Eared Slider": "Long-lived turtle needing UV light, water care, and basking space.",
    "Syrian Hamster": "Independent small pet, active at night, and should usually live alone.",
}


def _info_tile_v10(parent, label, value, color=None):
    color = color or COLORS["teal"]
    tile = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=18, border_width=1, border_color="#E5E7EB")
    ctk.CTkLabel(tile, text=label, text_color=COLORS["muted"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
    ctk.CTkLabel(tile, text=display(value) or "Not specified", text_color=color, font=("Segoe UI", 18, "bold"), wraplength=210, justify="left").pack(anchor="w", padx=16, pady=(0, 14))
    return tile


def _section_card_v10(parent, title, body, accent=None):
    accent = accent or COLORS["orange"]
    card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=22, border_width=1, border_color="#E5E7EB")
    top = ctk.CTkFrame(card, fg_color="transparent")
    top.pack(fill="x", padx=18, pady=(16, 4))
    ctk.CTkLabel(top, text="●", text_color=accent, font=("Segoe UI", 18, "bold")).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(top, text=title, text_color=COLORS["dark"], font=("Segoe UI", 18, "bold")).pack(side="left")
    ctk.CTkLabel(card, text=body, text_color=COLORS["muted"], font=("Segoe UI", 15), wraplength=500, justify="left").pack(anchor="w", padx=20, pady=(4, 18))
    return card


def _show_pet_detail_v10(self, pet_id):
    """Clickable Shopify-style pet profile page with scroll reset and rich pet attributes."""
    self.clear_page()
    _reset_scroll_to_top(self)
    assert self.db is not None

    try:
        pet = self.db.one(
            """
            SELECT p.pet_id, p.pet_name, p.age, p.gender, p.color, p.size_label, p.rescue_date,
                   p.description, p.health_status, p.availability_status, p.shelter_id, p.breed_id,
                   b.breed_name, c.category_name, s.shelter_name, s.location, s.contact_no,
                   (SELECT image_url FROM pet_image pi WHERE pi.pet_id=p.pet_id AND ROWNUM=1) AS image_url
            FROM pet p
            JOIN breed b ON b.breed_id=p.breed_id
            JOIN pet_category c ON c.category_id=b.category_id
            JOIN shelter s ON s.shelter_id=p.shelter_id
            WHERE p.pet_id=:pet_id
            """,
            {"pet_id": pet_id},
        )
        if not pet:
            messagebox.showerror("Missing", "Pet not found.", parent=self)
            self.show_pets()
            return

        category = display(pet.get("category_name")) or "Pet"
        breed = display(pet.get("breed_name")) or "Unknown Breed"
        guide = PET_GUIDES.get(category, PET_GUIDES.get("Dog"))
        breed_note = BREED_NOTES.get(breed, f"{breed} has individual personality traits that should be observed during adoption counseling.")

        # Header
        self.page_header(
            pet["pet_name"],
            f"Complete adoption profile • {category} • {breed} • {pet['shelter_name']}"
        )

        # Product/profile hero
        hero = ctk.CTkFrame(self.page, fg_color="#FFFFFF", corner_radius=32, border_width=1, border_color="#E5E7EB")
        hero.pack(fill="x", padx=30, pady=(0, 26))
        hero.grid_columnconfigure(0, weight=0)
        hero.grid_columnconfigure(1, weight=1)

        img = self.make_image(pet.get("image_url"), pet.get("pet_name", "Pet"), category, size=(560, 390))
        image_box = ctk.CTkFrame(hero, fg_color="#FFF7ED", corner_radius=28)
        image_box.grid(row=0, column=0, rowspan=2, sticky="n", padx=26, pady=26)
        ctk.CTkLabel(image_box, image=img, text="").pack(padx=14, pady=14)

        info = ctk.CTkFrame(hero, fg_color="transparent")
        info.grid(row=0, column=1, sticky="nsew", padx=(0, 28), pady=(28, 18))
        ctk.CTkLabel(info, text="Fur Ever Paws Pet Profile", text_color=COLORS["orange2"], font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ctk.CTkLabel(info, text=pet["pet_name"], text_color=COLORS["dark"], font=("Segoe UI", 42, "bold")).pack(anchor="w", pady=(4, 4))
        ctk.CTkLabel(info, text=f"{category} • {breed}", text_color=COLORS["teal2"], font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(
            info,
            text=display(pet.get("description")) or "This pet is waiting for a safe and loving home.",
            text_color=COLORS["muted"],
            font=("Segoe UI", 17),
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        # Status chips arranged in grid, not squeezed horizontally
        chips = ctk.CTkFrame(info, fg_color="transparent")
        chips.pack(fill="x", pady=(0, 14))
        chip_data = [
            (f"Availability: {pet['availability_status']}", COLORS["green"] if pet["availability_status"] == "Available" else COLORS["yellow"]),
            (f"Health: {pet['health_status']}", COLORS["green"] if pet["health_status"] == "Healthy" else COLORS["rose"]),
            (f"Age: {display(pet['age'])} years", COLORS["purple"]),
            (f"Gender: {pet['gender']}", COLORS["blue"]),
        ]
        for i, (txt, color) in enumerate(chip_data):
            ctk.CTkLabel(chips, text=txt, fg_color=color, text_color="#FFFFFF", corner_radius=18, padx=14, pady=7, font=("Segoe UI", 13, "bold")).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 10), pady=5)

        actions = ctk.CTkFrame(info, fg_color="transparent")
        actions.pack(anchor="w", pady=(4, 0))
        ctk.CTkButton(actions, text="← Back to Gallery", height=42, fg_color=COLORS["muted"], hover_color="#4B5563", corner_radius=16, command=self.show_pets).pack(side="left", padx=(0, 10))
        if self.role() == "Adopter" and pet["availability_status"] == "Available":
            ctk.CTkButton(actions, text="Apply for Adoption", height=42, fg_color=COLORS["orange"], hover_color=COLORS["orange2"], corner_radius=16, command=lambda p=pet: self.apply_for_pet(p)).pack(side="left")

        # Quick facts
        facts = ctk.CTkFrame(self.page, fg_color="transparent")
        facts.pack(fill="x", padx=30, pady=(0, 24))
        facts.grid_columnconfigure((0, 1, 2, 3), weight=1)
        fact_items = [
            ("Expected Lifetime", guide["lifespan"], COLORS["orange2"]),
            ("Color", pet.get("color"), COLORS["teal2"]),
            ("Size", pet.get("size_label"), COLORS["purple"]),
            ("Rescue Date", pet.get("rescue_date"), COLORS["blue"]),
            ("Shelter", pet.get("shelter_name"), COLORS["green2"]),
            ("Location", pet.get("location"), COLORS["teal2"]),
            ("Contact", pet.get("contact_no"), COLORS["rose"]),
            ("Breed", breed, COLORS["purple"]),
        ]
        for i, (label, value, color) in enumerate(fact_items):
            tile = _info_tile_v10(facts, label, value, color)
            tile.grid(row=i // 4, column=i % 4, sticky="nsew", padx=8, pady=8)

        # Care and behavior description cards
        ctk.CTkLabel(self.page, text="Characteristics & Care Guide", text_color=COLORS["dark"], font=("Segoe UI", 30, "bold")).pack(anchor="w", padx=34, pady=(4, 10))
        guide_grid = ctk.CTkFrame(self.page, fg_color="transparent")
        guide_grid.pack(fill="x", padx=30, pady=(0, 24))
        guide_grid.grid_columnconfigure((0, 1), weight=1)
        sections = [
            ("Breed Personality", breed_note, COLORS["orange"]),
            ("Temperament", guide["temperament"], COLORS["teal"]),
            ("Living Environment", guide["environment"], COLORS["blue"]),
            ("Care Requirements", guide["care"], COLORS["purple"]),
            ("Diet Notes", guide["diet"], COLORS["green"]),
            ("Activity Level", guide["activity"], COLORS["rose"]),
        ]
        for i, (title, body, accent) in enumerate(sections):
            card = _section_card_v10(guide_grid, title, body, accent)
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)

        # Medical and vaccination summary
        med = self.db.all(
            """
            SELECT mr.medical_record_id, ua.full_name AS veterinarian, mr.checkup_date,
                   mr.diagnosis, mr.treatment, mr.health_notes
            FROM medical_record mr
            JOIN veterinarian v ON v.vet_id=mr.vet_id
            JOIN user_account ua ON ua.user_id=v.user_id
            WHERE mr.pet_id=:pet_id
            ORDER BY mr.checkup_date DESC, mr.medical_record_id DESC
            """,
            {"pet_id": pet_id},
        )
        vac = self.db.all(
            """
            SELECT vr.vaccination_id, ua.full_name AS veterinarian, vr.vaccine_name,
                   vr.vaccination_date, vr.next_due_date
            FROM vaccination_record vr
            JOIN veterinarian v ON v.vet_id=vr.vet_id
            JOIN user_account ua ON ua.user_id=v.user_id
            WHERE vr.pet_id=:pet_id
            ORDER BY vr.vaccination_date DESC, vr.vaccination_id DESC
            """,
            {"pet_id": pet_id},
        )

        ctk.CTkLabel(self.page, text="Medical History", text_color=COLORS["dark"], font=("Segoe UI", 30, "bold")).pack(anchor="w", padx=34, pady=(6, 10))
        self.render_table(med, ["medical_record_id", "veterinarian", "checkup_date", "diagnosis", "treatment", "health_notes"], height=6)

        ctk.CTkLabel(self.page, text="Vaccination History", text_color=COLORS["dark"], font=("Segoe UI", 30, "bold")).pack(anchor="w", padx=34, pady=(6, 10))
        self.render_table(vac, ["vaccination_id", "veterinarian", "vaccine_name", "vaccination_date", "next_due_date"], height=6)

        self.after(80, lambda: _reset_scroll_to_top(self))
    except Exception as exc:
        messagebox.showerror("Pet Profile Error", f"Could not load pet profile.\n\n{exc}", parent=self)
        self.show_pets()


# Apply final v10 profile/scroll overrides.
PremiumPetAdoptionApp.clear_page = _clear_page_v10
PremiumPetAdoptionApp.show_pet_detail = _show_pet_detail_v10


# ----------------------------------------------------------------------
# FINAL v11: fixed pet profile layout
# This override removes the clipped horizontal profile layout and keeps the
# Shopify-style profile readable inside the app content area.
# ----------------------------------------------------------------------
def _color_v11(name, fallback="#0F766E"):
    return COLORS.get(name, fallback)


def _small_chip_v11(parent, label, value, color):
    chip = ctk.CTkFrame(parent, fg_color=color, corner_radius=18)
    ctk.CTkLabel(
        chip,
        text=label,
        text_color="#FFFFFF",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w", padx=16, pady=(8, 0))
    ctk.CTkLabel(
        chip,
        text=display(value) or "Not set",
        text_color="#FFFFFF",
        font=("Segoe UI", 15, "bold"),
        wraplength=150,
        justify="left",
    ).pack(anchor="w", padx=16, pady=(0, 9))
    return chip


def _profile_fact_v11(parent, icon, title, value, color):
    card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=20, border_width=1, border_color="#E5E7EB")
    ctk.CTkLabel(card, text=icon, text_color=color, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=18, pady=(14, 0))
    ctk.CTkLabel(card, text=title, text_color=COLORS["muted"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(2, 0))
    ctk.CTkLabel(card, text=display(value) or "Not specified", text_color=COLORS["dark"], font=("Segoe UI", 16, "bold"), wraplength=210, justify="left").pack(anchor="w", padx=18, pady=(2, 16))
    return card


def _description_card_v11(parent, title, body, icon, accent):
    card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=22, border_width=1, border_color="#E5E7EB")
    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=18, pady=(16, 6))
    ctk.CTkLabel(header, text=icon, text_color=accent, font=("Segoe UI", 22, "bold")).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(header, text=title, text_color=COLORS["dark"], font=("Segoe UI", 18, "bold")).pack(side="left")
    ctk.CTkLabel(card, text=body, text_color=COLORS["muted"], font=("Segoe UI", 15), wraplength=460, justify="left").pack(anchor="w", padx=20, pady=(2, 18))
    return card


def _show_pet_detail_v11(self, pet_id):
    """Final presentation-quality pet detail page with no clipping."""
    self.clear_page()
    _reset_scroll_to_top(self)
    assert self.db is not None

    try:
        pet = self.db.one(
            """
            SELECT p.pet_id, p.pet_name, p.age, p.gender, p.color, p.size_label, p.rescue_date,
                   p.description, p.health_status, p.availability_status, p.shelter_id, p.breed_id,
                   b.breed_name, c.category_name, s.shelter_name, s.location, s.contact_no,
                   (SELECT image_url FROM pet_image pi WHERE pi.pet_id=p.pet_id AND ROWNUM=1) AS image_url
            FROM pet p
            JOIN breed b ON b.breed_id=p.breed_id
            JOIN pet_category c ON c.category_id=b.category_id
            JOIN shelter s ON s.shelter_id=p.shelter_id
            WHERE p.pet_id=:pet_id
            """,
            {"pet_id": pet_id},
        )
        if not pet:
            messagebox.showerror("Missing", "Pet not found.", parent=self)
            self.show_pets()
            return

        category = display(pet.get("category_name")) or "Pet"
        breed = display(pet.get("breed_name")) or "Unknown Breed"
        guide = PET_GUIDES.get(category, PET_GUIDES.get("Dog", {}))
        breed_note = BREED_NOTES.get(breed, f"{breed} has individual personality traits that should be discussed with the shelter staff before adoption.")
        description = display(pet.get("description")) or "This pet is waiting for a safe, stable, and loving home."

        self.page_header(
            f"{pet['pet_name']} Profile",
            f"Detailed adoption profile for {category.lower()} lovers"
        )

        # Responsive top profile card. Smaller image + fixed text wrap prevents clipping.
        hero = ctk.CTkFrame(self.page, fg_color="#FFFFFF", corner_radius=32, border_width=1, border_color="#E5E7EB")
        hero.pack(fill="x", padx=30, pady=(0, 24))
        hero.grid_columnconfigure(0, weight=1, minsize=470)
        hero.grid_columnconfigure(1, weight=1, minsize=430)

        left = ctk.CTkFrame(hero, fg_color="#FFF7ED", corner_radius=28)
        left.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        img = self.make_image(pet.get("image_url"), pet.get("pet_name", "Pet"), category, size=(430, 310))
        ctk.CTkLabel(left, image=img, text="").pack(padx=18, pady=18)

        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 24), pady=24)
        ctk.CTkLabel(right, text="Fur Ever Paws Adoption Profile", text_color=COLORS["orange2"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(right, text=pet["pet_name"], text_color=COLORS["dark"], font=("Segoe UI", 44, "bold")).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(right, text=f"{category} • {breed}", text_color=COLORS["teal2"], font=("Segoe UI", 22, "bold"), wraplength=420, justify="left").pack(anchor="w", pady=(2, 12))
        ctk.CTkLabel(right, text=description, text_color=COLORS["muted"], font=("Segoe UI", 16), wraplength=430, justify="left").pack(anchor="w", pady=(0, 14))

        chips = ctk.CTkFrame(right, fg_color="transparent")
        chips.pack(fill="x", pady=(0, 14))
        chips.grid_columnconfigure((0, 1), weight=1)
        chip_items = [
            ("Availability", pet.get("availability_status"), _color_v11("green") if pet.get("availability_status") == "Available" else _color_v11("yellow")),
            ("Health", pet.get("health_status"), _color_v11("green") if pet.get("health_status") == "Healthy" else _color_v11("rose")),
            ("Age", f"{display(pet.get('age'))} years", _color_v11("purple")),
            ("Gender", pet.get("gender"), _color_v11("blue")),
        ]
        for i, item in enumerate(chip_items):
            _small_chip_v11(chips, *item).grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)

        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.pack(anchor="w", pady=(4, 0))
        ctk.CTkButton(actions, text="← Back to Gallery", height=44, fg_color=COLORS["muted"], hover_color="#4B5563", corner_radius=16, command=self.show_pets).pack(side="left", padx=(0, 10))
        if self.role() == "Adopter" and pet.get("availability_status") == "Available":
            ctk.CTkButton(actions, text="Apply for Adoption", height=44, fg_color=COLORS["orange"], hover_color=COLORS["orange2"], corner_radius=16, command=lambda p=pet: self.apply_for_pet(p)).pack(side="left")

        # Facts section
        ctk.CTkLabel(self.page, text="Pet Facts", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=34, pady=(0, 10))
        facts = ctk.CTkFrame(self.page, fg_color="transparent")
        facts.pack(fill="x", padx=30, pady=(0, 24))
        facts.grid_columnconfigure((0, 1, 2, 3), weight=1)
        fact_items = [
            ("⏳", "Expected Lifetime", guide.get("lifespan", "Varies by pet type"), _color_v11("orange2")),
            ("🎨", "Color", pet.get("color"), _color_v11("teal2")),
            ("📏", "Size", pet.get("size_label"), _color_v11("purple")),
            ("🗓", "Rescue Date", pet.get("rescue_date"), _color_v11("blue")),
            ("🏠", "Shelter", pet.get("shelter_name"), _color_v11("green")),
            ("📍", "Location", pet.get("location"), _color_v11("teal2")),
            ("☎", "Contact", pet.get("contact_no"), _color_v11("rose")),
            ("🧬", "Breed", breed, _color_v11("purple")),
        ]
        for i, item in enumerate(fact_items):
            _profile_fact_v11(facts, *item).grid(row=i // 4, column=i % 4, sticky="nsew", padx=8, pady=8)

        # About and care section
        ctk.CTkLabel(self.page, text="About & Care Guide", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=34, pady=(0, 10))
        guide_grid = ctk.CTkFrame(self.page, fg_color="transparent")
        guide_grid.pack(fill="x", padx=30, pady=(0, 24))
        guide_grid.grid_columnconfigure((0, 1), weight=1)
        sections = [
            ("Breed Personality", breed_note, "🐾", _color_v11("orange")),
            ("Temperament", guide.get("temperament", "Every pet has its own personality and should be introduced carefully."), "💛", _color_v11("teal")),
            ("Living Environment", guide.get("environment", "Needs a safe, clean, and comfortable home environment."), "🏡", _color_v11("blue")),
            ("Care Requirements", guide.get("care", "Needs regular feeding, cleaning, attention, and monitoring."), "🧼", _color_v11("purple")),
            ("Diet Notes", guide.get("diet", "Diet should follow species and vet recommendations."), "🥣", _color_v11("green")),
            ("Activity Level", guide.get("activity", "Activity needs depend on age, breed, and health."), "⚡", _color_v11("rose")),
        ]
        for i, item in enumerate(sections):
            _description_card_v11(guide_grid, *item).grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)

        # Medical and vaccination summary
        med = self.db.all(
            """
            SELECT mr.medical_record_id, ua.full_name AS veterinarian, mr.checkup_date,
                   mr.diagnosis, mr.treatment, mr.health_notes
            FROM medical_record mr
            JOIN veterinarian v ON v.vet_id=mr.vet_id
            JOIN user_account ua ON ua.user_id=v.user_id
            WHERE mr.pet_id=:pet_id
            ORDER BY mr.checkup_date DESC, mr.medical_record_id DESC
            """,
            {"pet_id": pet_id},
        )
        vac = self.db.all(
            """
            SELECT vr.vaccination_id, ua.full_name AS veterinarian, vr.vaccine_name,
                   vr.vaccination_date, vr.next_due_date
            FROM vaccination_record vr
            JOIN veterinarian v ON v.vet_id=vr.vet_id
            JOIN user_account ua ON ua.user_id=v.user_id
            WHERE vr.pet_id=:pet_id
            ORDER BY vr.vaccination_date DESC, vr.vaccination_id DESC
            """,
            {"pet_id": pet_id},
        )

        ctk.CTkLabel(self.page, text="Medical History", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=34, pady=(0, 10))
        self.render_table(med, ["medical_record_id", "veterinarian", "checkup_date", "diagnosis", "treatment", "health_notes"], height=6)

        ctk.CTkLabel(self.page, text="Vaccination History", text_color=COLORS["dark"], font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=34, pady=(0, 10))
        self.render_table(vac, ["vaccination_id", "veterinarian", "vaccine_name", "vaccination_date", "next_due_date"], height=6)

        self.after(80, lambda: _reset_scroll_to_top(self))

    except Exception as exc:
        messagebox.showerror("Pet Profile Error", f"Could not load pet profile.\n\n{exc}", parent=self)
        self.show_pets()


PremiumPetAdoptionApp.show_pet_detail = _show_pet_detail_v11


if __name__ == "__main__":
    app = PremiumPetAdoptionApp()
    app.mainloop()
