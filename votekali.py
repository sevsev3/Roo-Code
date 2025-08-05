review and fix this python User vote system code to the end and make sure it is in a logical way. There is database.py, operators.py and most importantly votekali.py I need this all to be structured correctly in one code i need all functions !

# ─── Standarta bibliotēka ────
import asyncio, logging, os, sys, json, time, urllib.parse
from enum import Enum
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ─── Trešo-pušu bibliotēkas (pip) ───────
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode, ContentType
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, User
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from aiogram.utils.keyboard import InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties

# ─── Lokālie moduļi ───────────────
from operators import router as operators_router
from constants import put, get
from database import _db
from states import (
    UserStates, CommentStates, ShopStates,
    ProductStates, AdminStates,
)
from aiogram.types import Message
from aiogram import F, Router
from operators import get_top_operators_page  # Importē funkciju no operators.py

router = Router()
dp.include_router(router)
dp.include_router(operators_router)

# ─── Konstantes / iestatījumi ──────────
BOT_TOKEN   = "7749785155:AAFR6kaBkHPa-SeiaoHMWe-wNtkakMGGQkI"

ADMIN_IDS = [7270387859, 7824389419, 7589646106]

OPERATOR_IDS = [
    7785261747, 7743719365, 7783853932, 7688149959,
    7860021728, 7681070242, 8127781804, 7695011473,
    7833175587, 7963283547, 6412139444, 7658529769,
    7755545122, 7656192052, 2730531727, 7608034729
]

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("kali_network_marketplace.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

~ $ cat database.py
# database.py — viena, tīra versija
import aiosqlite
from typing import Dict, Any, List, Optional
from aiogram import F
from aiogram.types import ContentType, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states import ShopStates

DB_FILE = "kali_network_marketplace.sqlite"

class SQLiteDB:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS operators (
                id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                votes INTEGER DEFAULT 0,
                deep_link_id INTEGER UNIQUE
            );

            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'user',
                referral_code TEXT,
                created_at TEXT,
                last_activity TEXT
            );

            CREATE TABLE IF NOT EXISTS shops(
                shop_id TEXT PRIMARY KEY,
                owner_id INTEGER,
                name TEXT,
                about TEXT,
                logo TEXT,
                banner TEXT,
                buttons TEXT,
                category TEXT,
                tags TEXT,
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS products(
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id TEXT,
                name TEXT,
                description TEXT,
                photo TEXT,
                video TEXT,
                buttons TEXT,
                category TEXT,
                stock TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS votes(
                vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                operator_id INTEGER,
                vote INTEGER,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS comments(
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                operator_id INTEGER,
                text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports(
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reason TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                emoji TEXT
            );
            """)
            await db.commit()

    # ---------- CRUD ----------
    async def insert_one(self, table: str, data: Dict[str, Any]) -> None:
        keys = ", ".join(data)
        qs = ", ".join("?" for _ in data)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"INSERT INTO {table} ({keys}) VALUES ({qs})", list(data.values()))
            await db.commit()

    async def find_one(self, table: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        res = await self.find(table, query, limit=1)
        return res[0] if res else None

    async def find(self, table: str,
                   query: Dict[str, Any] | None = None,
                   limit: int = 0) -> List[Dict[str, Any]]:
        if query:
            where = " AND ".join(f"{k}=?" for k in query)
            sql, params = f"SELECT * FROM {table} WHERE {where}", list(query.values())
        else:
            sql, params = f"SELECT * FROM {table}", []
        if limit:
            sql += f" LIMIT {limit}"
        async with aiosqlite.connect(self.db_path) as db, db.execute(sql, params) as cur:
            rows = await cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]

    async def update_one(self, table: str,
                         update: Dict[str, Any],
                         where: Dict[str, Any]) -> None:
        set_parts = []
        values = []

        for key, value in update.items():
            if isinstance(value, str) and value.strip().startswith(f"{key} +"):
                set_parts.append(f"{key} = {value}")
            else:
                set_parts.append(f"{key} = ?")
                values.append(value)

        where_clause = " AND ".join([f"{k} = ?" for k in where])
        values.extend(where.values())

        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_clause}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, values)
            await db.commit()

    async def delete_one(self, table: str, query: Dict[str, Any]) -> None:
        where = " AND ".join(f"{k}=?" for k in query)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"DELETE FROM {table} WHERE {where}", list(query.values()))
            await db.commit()

# --------- Globālais objekts ---------
_db = SQLiteDB()

# Palaist automātisko tabulu izveidi
async def init():
    await _db.init_db()

if __name__ == "__main__":
    import asyncio
    asyncio.run(init())
    

# ─── Bot + Dispatcher + Router ───
bot = Bot(BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher(storage=MemoryStorage())

# === ENUMS ==
class UserRole(Enum):
    USER = "user"
    OPERATOR = "operator"
    ADMIN = "admin"
    MODERATOR = "moderator"

class VendorStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    PENDING = "pending"
    VERIFIED = "verified"

class VoteType(Enum):
    UPVOTE = 1

# === Startup function ===
async def on_startup() -> None:
    await _db.init_db()
    logger.info("✅ Database initialized")

    async def find(self, table: str, query: Optional[Dict[str, Any]] = None,
                   sort_by: Optional[str] = None, sort_desc: bool = False,
                   limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                sql = f"SELECT * FROM {table}"
                params: List[Any] = []
                if query:
                    where_clauses: List[str] = []
                    for k, v in query.items():
                        if isinstance(v, (list, tuple)):
                            placeholders = ','.join('?' * len(v))
                            where_clauses.append(f"{k} IN ({placeholders})")
                            params.extend(list(v))
                        elif isinstance(v, str) and v.startswith('%') and v.endswith('%'):
                            where_clauses.append(f"{k} LIKE ?")
                            params.append(v)
                        else:
                            where_clauses.append(f"{k}=?")
                            params.append(v)
                    sql += f" WHERE {' AND '.join(where_clauses)}"
                if sort_by:
                    sql += f" ORDER BY {sort_by} {'DESC' if sort_desc else 'ASC'}"
                if limit:
                    sql += f" LIMIT {limit}"
                    if offset:
                        sql += f" OFFSET {offset}"
                cursor = await db.execute(sql, params)
                rows = await cursor.fetchall()
                if not rows:
                    return []
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error in find query for table {table}: {e}")
            return []

    async def find_one(self, table: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        results = await self.find(table, query, limit=1)
        return results[0] if results else None

    async def insert_one(self, table: str, data: Dict[str, Any]) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                keys = ", ".join(data.keys())
                placeholders = ", ".join("?" for _ in data)
                sql = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
                await db.execute(sql, list(data.values()))
                await db.commit()
                return True
        except Exception as e:
            logging.error(f"Error in insert_one for table {table}: {e}")
            return False

    async def update_one(self, table: str, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                set_clauses = [f"{k}=?" for k in update.keys()]
                set_values = list(update.values())
                where_clauses = [f"{k}=?" for k in query.keys()]
                where_values = list(query.values())
                sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
                await db.execute(sql, set_values + where_values)
                await db.commit()
                return True
        except Exception as e:
            logging.error(f"Error in update_one for table {table}: {e}")
            return False

    async def delete_one(self, table: str, query: Dict[str, Any]) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                where_clauses = [f"{k}=?" for k in query.keys()]
                sql = f"DELETE FROM {table} WHERE {' AND '.join(where_clauses)}"
                await db.execute(sql, list(query.values()))
                await db.commit()
                return True
        except Exception as e:
            logging.error(f"Error in delete_one for table {table}: {e}")
            return False

    async def delete_many(self, table: str, query: Optional[Dict[str, Any]] = None) -> bool:
        """Delete multiple records"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if query:
                    where_clauses: List[str] = []
                    params: List[Any] = []
                    for k, v in query.items():
                        where_clauses.append(f"{k}=?")
                        params.append(v)
                    sql = f"DELETE FROM {table} WHERE {' AND '.join(where_clauses)}"
                    await db.execute(sql, params)
                else:
                    await db.execute(f"DELETE FROM {table}")

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Error in delete_many for table {table}: {e}")
            return False

    async def count_documents(self, table: str, query: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                sql = f"SELECT COUNT(*) FROM {table}"
                params: List[Any] = []

                if query:
                    where_clauses: List[str] = []
                    for k, v in query.items():
                        where_clauses.append(f"{k}=?")
                        params.append(v)
                    sql += f" WHERE {' AND '.join(where_clauses)}"

                cursor = await db.execute(sql, params)
                result = await cursor.fetchone()
                return result[0] if result else 0

        except Exception as e:
            logger.error(f"Error in count_documents for table {table}: {e}")
            return 0

    async def execute_raw(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(sql, params or [])
                rows = await cursor.fetchall()

                if not rows:
                    return []

                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, row)) for row in rows]

        except Exception as e:
            logger.error(f"Error in execute_raw: {e}")
            return []

# === FSM STATES ===
class UserStates(StatesGroup):
    waiting_for_feedback = State()
    waiting_for_report_reason = State()
    waiting_for_support_message = State()

class CommentStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_rating = State()
    waiting_for_reply = State()

class ShopStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_about = State()
    waiting_for_logo = State()
    waiting_for_banner = State()
    waiting_for_buttons = State()
    waiting_for_category = State()
    waiting_for_tags = State()

class ProductStates(StatesGroup):
    waiting_for_name        = State()
    waiting_for_info        = State()
    waiting_for_price       = State()
    waiting_for_photo       = State()
    waiting_for_video       = State()
    waiting_for_buttons     = State()
    waiting_for_category    = State()
    waiting_for_stock       = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_ban_reason = State()
    waiting_for_category_name = State()
    waiting_for_backup_confirmation = State()

class Up(StatesGroup):
    waiting_kind = State()
    waiting_key  = State()
    waiting_file = State()

class MediaUpload(StatesGroup):
    waiting_kind = State()
    waiting_key  = State()
    waiting_file = State()

# === Storage init ===
from votekali.storage import KaliNetworkStorage
db = KaliNetworkStorage()

# === UTILITY FUNCTIONS ===
def validate_url(url: str) -> bool:
    """Validate URL format with enhanced checking"""

    try:
        result = urllib.parse.urlparse(url)
        return bool(result.scheme and result.netloc and result.scheme in ['http', 'https'])
    except Exception:
        return False
    try:

        result = urllib.parse.urlparse(url)
        return bool(result.scheme and result.netloc and result.scheme in ['http', 'https'])
    except Exception:
        return False

def generate_referral_code(user_id: int) -> str:
    """Generate unique referral code"""
    return "KNC{user_id}{random.randint(1000, 9999)}"

def calculate_reputation_score(votes_received: int, votes_given: int,
                             shops_owned: int, comments_made: int) -> int:
    """Calculate user reputation score"""
    base_score = votes_received * 10
    activity_bonus = (votes_given + comments_made) * 2
    shop_bonus = shops_owned * 50
    return max(0, base_score + activity_bonus + shop_bonus)

def format_datetime(dt_string: str) -> str:
    """Format datetime string for display"""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_string

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    return text[:max_length] + "..." if len(text) > max_length else text

async def log_analytics_event(event_type: str, user_id: Optional[int] = None,
                            shop_id: Optional[str] = None, product_id: Optional[int] = None,
                            data: Optional[Dict[str, Any]] = None) -> None:

    """Log analytics event"""
    try:
        await db.insert_one("analytics", {
            "event_type": event_type,
            "user_id": user_id,
            "shop_id": shop_id,
            "product_id": product_id,
            "data": json.dumps(data or {}),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error logging analytics event: {e}")

async def send_notification(user_id: int, title: str, message: str,
                          notification_type: str = "info", action_url: Optional[str] = None) -> None:
    """Send notification to user"""
    try:
        await db.insert_one("notifications", {
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "action_url": action_url,
            "date": datetime.now().isoformat()

        })
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

async def ensure_user_exists(user: User) -> None:
    """Ensure user exists in database"""

    try:
        existing_user = await db.find_one("users", {"user_id": user.id})
        if not existing_user:
            role = UserRole.ADMIN.value if user.id in ADMIN_IDS else \
                   UserRole.OPERATOR.value if user.id in OPERATOR_IDS else \
                   UserRole.USER.value

            referral_code = generate_referral_code(user.id)

            await db.insert_one("users", {
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": role,
                "referral_code": referral_code,
                "registration_date": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat()
            })

            # Send welcome notification
            await send_notification(
                user.id,
                "Welcome to KNC228 NETWORK! 🎉",
                f"Welcome {user.first_name}! Your referral code: {referral_code}"
            )
        else:
            # Update last activity
            await db.update_one("users", {"user_id": user.id}, {
                "last_activity": datetime.now().isoformat(),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            })
    except Exception as e:
        logger.error(f"Error ensuring user exists: {e}")

async def ensure_shop_exists(user_id: int) -> bool:
    """Ensure operator has a shop"""
    try:
        user = await db.find_one("users", {"user_id": user_id})
        if not user or user.get("role") not in [UserRole.OPERATOR.value, UserRole.ADMIN.value]:
            return False

        existing_shop = await db.find_one("shops", {"owner_id": user_id})
        if not existing_shop:
            shop_id = f"shop_{user_id}_{int(time.time())}"
            shop_data: Dict[str, Any] = {
                "shop_id": shop_id,
                "owner_id": user_id,
                "name": f"{user.get('first_name', 'Unknown')}'s Shop",
                "about": "Welcome to my shop!",
                "category": "General",
                "status": ShopStatus.ACTIVE.value,
                "created_date": datetime.now().isoformat(),
                "updated_date": datetime.now().isoformat()
            }

            success = await db.insert_one("shops", shop_data)
            if success:
                await db.update_one("users", {"user_id": user_id}, {"shops_owned": 1})
                await log_analytics_event("shop_created", user_id, shop_id)
                return True
        return True
    except Exception as e:
        logger.error(f"Error ensuring shop exists: {e}")
        return False

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ——— MAIN KEYBOARD —————————————————————————————
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ RATINGS ⭐"),    KeyboardButton(text="📋 CATEGORIES 📋")],
        [KeyboardButton(text="☎️ CONTACTS ☎️"),  KeyboardButton(text="🔑 ACCOUNT 🔑")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)
@router.message(Command("start"))
async def cmd_start(message: Message):
    photo   = FSInputFile("welcome.jpg")
    caption = (
        "🔥 Welcome to KALI NETWORK catalogue\n"
        "Here you can find Legit and Trusted Vendors across all Baltic States 🇱🇻🇪🇪🇱🇹\n\n"
        "⚠️ Always check before making any deal – make sure the username is not just in the bio.\n\n"
        "🖤 Thank you for being part of the Kali Network"
    )
    await message.answer_photo(photo=photo, caption=caption, reply_markup=main_kb)

# ——— RATINGS ——————————————————————————————————————
@router.message(F.text == "⭐ RATINGS ⭐")
async def ratings_handler(message: Message):
    top = await db.get_top_operators()
    if not top:
        return await message.answer(
            "❌ Šobrīd nav neviena operatora sarakstā.",
            reply_markup=main_kb
        )

    text = "<b>⭐ TOP operatori:</b>\n\n"
    for i, (user_id, username, votes) in enumerate(top, start=1):
        name = f"@{username}" if username else f"ID {user_id}"
        text += f"{i}. {name} — {votes} ⭐\n"

    await message.answer(text, reply_markup=main_kb)

@router.message(F.text == "⭐ RATINGS")
async def show_ratings(message: Message) -> None:
    try:
        shops_list = await _db.find("shops", sort_by="votes", sort_desc=True, limit=10)
        if not shops_list:
            await message.answer("No shops available for rating.")
            return

        markup = InlineKeyboardMarkup(inline_keyboard=[])
        for shop in shops_list:
            shop_id_str = shop["shop_id"].replace("shop_", "")
            votes_count = shop.get("votes", 0)
            name = shop.get("name", shop_id_str)
            markup.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"{name} ⭐({votes_count})",
                    callback_data=f"shop_{shop_id_str}"
                )
            ])

        await message.answer("⭐ Vote for your favorite shop!", reply_markup=markup)

    except Exception as e:
        logging.error(f"Error fetching shops for ratings: {e}")
        await message.answer("❌ Database error, please try again later.")

@router.message(F.text == "📋 CATEGORIES")
async def show_categories(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💊 Pills",    callback_data="cat_pills")],
    [InlineKeyboardButton(text="🌿 Weed",     callback_data="cat_weed")],
    [InlineKeyboardButton(text="🛠 Services", callback_data="cat_services")],
    ])
    await message.answer("📋 Choose category:", reply_markup=kb)

async def generate_shop_card(message, shop):
    name = shop.get("name", "Unknown")
    votes = len(shop.get("voters", []))
    logo_id = shop.get("logo_file_id", None)
    user_id = shop.get("user_id")
    buttons = shop.get("buttons", [])
    stars = get_star_rating(votes)

    text = f"<b>{name}</b>\n{stars} ({votes} votes)"

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(text="⭐ Vote", callback_data=f"vote_{user_id}"))
    if buttons:
        kb.insert(InlineKeyboardButton(text="🔗 Shop", url=buttons[0]['url']))
    kb.add(InlineKeyboardButton(text="⬅ Back", callback_data="back_to_menu"))

    if logo_id:
        await message.answer_photo(logo_id, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("shop_"))
async def open_shop(callback: CallbackQuery):
    shop_id = callback.data.split("_")[1]

    shops = load_json(SHOPS_FILE)
    if shop_id not in shops:
        await callback.answer("❌ Shop not found.", show_alert=True)
        return

    shop = shops[shop_id]
    text = f"<b>{shop['name']}</b>\n\n{shop.get('description', '—')}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 VIEW PRODUCTS", callback_data=f"products_{shop_id}")],
        [InlineKeyboardButton(text="💱 OTHER", callback_data=f"other_{shop_id}")],
        [InlineKeyboardButton(text="💬 COMMENTS", callback_data=f"comments_{shop_id}")],
        [
            InlineKeyboardButton(text="⬅️ BACK", callback_data="ratings_back"),
            InlineKeyboardButton(text="⭐ VOTE", callback_data=f"vote_{shop_id}")
        ]
    ])

    if shop.get("logo"):
        await callback.message.answer_photo(photo=shop["logo"], caption=text, reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()

# === Manage Shop Menu  ===
@router.callback_query(F.data == "manage_shop")
async def manage_shop(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 PRODUCT LIST", callback_data="products_list")],
        [InlineKeyboardButton(text="🧩 MAIN PAGE", callback_data="main_page")],
        [InlineKeyboardButton(text="🏷 TAGS", callback_data="shop_tags")],
        [InlineKeyboardButton(text="👤 OWNERS", callback_data="shop_owners")],
        [InlineKeyboardButton(text="🔗 MY SHOP LINK", callback_data="shop_link")],
        [InlineKeyboardButton(text="⭐ VOTERS", callback_data="shop_voters")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="account")],
        [InlineKeyboardButton(text="⛔ PAUSE", callback_data="pause_shop")]
    ])
    await callback.message.edit_text("🛠 Manage your shop using the buttons below:", reply_markup=kb)

# === Main Page Settings Menu ===
@router.callback_query(F.data == "main_page")
async def main_page_settings(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 SET LOGO", callback_data="set_logo"),
         InlineKeyboardButton(text="❌ DELETE LOGO", callback_data="delete_logo")],
        [InlineKeyboardButton(text="📝 SET ABOUT", callback_data="set_about"),
         InlineKeyboardButton(text="❌ DELETE ABOUT", callback_data="delete_about")],
        [InlineKeyboardButton(text="🔘 SET BUTTONS", callback_data="set_buttons"),
         InlineKeyboardButton(text="❌ DELETE BUTTONS", callback_data="delete_buttons")],
        [InlineKeyboardButton(text="🗿 ADD PRODUCT", callback_data="add_product"),
         InlineKeyboardButton(text="🗑️ DELETE PRODUCT", callback_data="delete_product")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="manage_shop"),
         InlineKeyboardButton(text="▶️ PREVIEW", callback_data="preview_shop")]
    ])
    await callback.message.edit_text("⚙️ Set up your main page:", reply_markup=kb)

# Begin adding a new product
@router.callback_query(F.data == "add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 Send ONE product photo (exactly 1 photo, not multiple):")
    await state.set_state(ProductStates.waiting_for_photo)

@router.message(F.content_type == ContentType.PHOTO, ProductStates.waiting_for_photo)
async def add_product_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer(
        "Now send full product description (name, info, price etc., max 500 characters):"
    )
    await state.set_state(ProductStates.waiting_for_info)

@router.message(F.content_type == ContentType.TEXT, ProductStates.waiting_for_info)

async def add_product_info(msg: Message, state: FSMContext) -> None:
    if len(msg.text) > 500:
        await msg.answer("❌ Description too long, max 500 characters.")
        return
    await state.update_data(info=msg.text)
    await msg.answer(
        "👉🏻 Send up to 3 inline buttons (each on a new line):\n"
        "Example:\nSupport - https://myshop.com\nWebsite - https://myshop.com"
    )
    await ProductStates.waiting_for_buttons.set()

@router.message(F.content_type == ContentType.TEXT, ProductStates.waiting_for_buttons)

async def add_product_buttons(msg: Message, state: FSMContext) -> None:
    btns: list[dict] = []
    for line in msg.text.strip().split("\n")[:3]:
        if " - " in line:
            text, url = line.split(" - ", 1)
            url = url.strip()
            if not validate_url(url):
                await msg.answer(f"❌ Invalid URL: {url}")
                return
            btns.append({"text": text.strip()[:64], "url": url})

    data = await state.get_data()
    user_id = msg.from_user.id
    try:
        # Save product to database
        product_data = {
            "shop_id": f"shop_{user_id}",
            "name": data.get("info", "").split("\n")[0][:100],  # First line as name
            "description": data.get("info", ""),
            "photo": data.get("photo"),
            "buttons": json.dumps(btns),
        }
        await _db.insert_one("products", product_data)
        await msg.answer("✅ Product successfully added to catalog.")
    except Exception as e:
        logging.error(f"Error adding product for user {user_id}: {e}")
        await msg.answer("❌ Database error, please try again later.")
    await state.finish()


# Show products of a shop
@router.callback_query(F.data.startswith("products_"))
async def show_products(callback: CallbackQuery) -> None:
    shop_id_str = callback.data.split("_", 1)[1]
    try:
        products = await _db.find("products", {"shop_id": f"shop_{shop_id_str}"})
        if not products:
            await callback.message.answer("This operator has no products yet.")
            return

        for prod in products:
            photo = prod.get("photo")
            info = prod.get("description", "No description")

            buttons = InlineKeyboardMarkup(inline_keyboard=[])
            try:
                button_data = json.loads(prod.get("buttons", "[]"))
                for btn in button_data:
                    buttons.inline_keyboard.append([
                        InlineKeyboardButton(text=btn.get("text"), url=btn.get("url"))
                    ])
            except Exception:
                pass

            if photo:
                await callback.message.answer_photo(
                    photo=photo, caption=info, reply_markup=buttons
                )
            else:
                await callback.message.answer(info, reply_markup=buttons)

    except Exception as e:
        logging.error(f"Error fetching products for shop_{shop_id_str}: {e}")
        await callback.message.answer("❌ Database error, please try again later.")

# ======= SET ABOUT ======= #
@router.callback_query(F.data == "set_about")
async def set_about(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "📝 Please send the text you want to set as your shop description (max 500 characters):"
    )
    await state.set_state(ShopStates.waiting_for_about)

@router.message(F.content_type == ContentType.TEXT, ShopStates.waiting_for_about)
async def receive_about_text(message: Message, state: FSMContext) -> None:
    if len(message.text) > 500:
        await message.answer("❌ Description too long, max 500 characters.")
        return
    user_id = message.from_user.id
    try:
        await _db.update_one(
            "shops",
            {"shop_id": f"shop_{user_id}"},
            {"about": message.text.strip()},
            upsert=True,
        )
        await message.answer("✅ Shop description saved successfully.")
    except Exception as e:
        logging.error(f"Error saving about for user {user_id}: {e}")
        await message.answer("❌ Database error, please try again later.")
    await state.clear()

@router.callback_query(F.data == "set_logo")
async def set_logo(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "🖼 Please send a photo, video, or gif to set as your shop logo:"
    )
    await state.set_state(ShopStates.waiting_for_logo)

@router.message(
    (F.content_type == ContentType.PHOTO) |
    (F.content_type == ContentType.VIDEO) |
    (F.content_type == ContentType.ANIMATION),
    ShopStates.waiting_for_logo
)
async def receive_logo(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    file_id: str | None = None

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.animation:
        file_id = message.animation.file_id

    if not file_id:
        await message.answer("❌ Invalid format. Please send a photo, video, or gif for the logo.")
        return

    try:
        await _db.update_one(
            "shops",
            {"shop_id": f"shop_{user_id}"},
            {"logo_file_id": file_id},
            upsert=True,
        )
        await message.answer("✅ Shop logo saved successfully.")
    except Exception as e:
        logging.error(f"Error saving logo for user {user_id}: {e}")
        await message.answer("❌ Database error, please try again later.")
    await state.clear()

# === COMMENT  ADDER === #
@router.callback_query(F.data.startswith("comment_"))
async def start_comment(callback: CallbackQuery, state: FSMContext):
    operator_id = int(callback.data.split("_")[1])
    await state.update_data(operator_id=operator_id)
    await callback.message.answer("💬 Enter your comment:")
    await state.set_state(CommentStates.waiting_for_comment)

# COMMENY
@router.message(CommentStates.waiting_for_comment)
async def receive_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    operator_id = data.get("operator_id")
    comment_text = message.text

    if not comment_text or len(comment_text) > 1000:
        await message.answer("Comment is too long (max 1000 characters).")
        return

    await _db.insert_one("comments", {
        "user_id": message.from_user.id,
        "operator_id": operator_id,
        "comment": comment_text,
        "timestamp": message.date.isoformat()
    })

    await message.answer("✅ Comment submitted!")
    await state.clear()

@router.callback_query(F.data.startswith("comments_"))
async def show_comments_handler(callback: CallbackQuery) -> None:
    shop_id_str = callback.data.split("_", 1)[1]
    try:
        comments = await _db.find(
            "comments", {"shop_id": f"shop_{shop_id_str}"}, limit=10
        )
        text = "<b>Comments about this shop:</b>\n\n"
        if not comments:
            text += "No comments yet."
        else:
            for com in comments:
                name = com.get("name", "Anonymous")
                comment = com.get("text", "")
                text += f"📦 <b>{name}</b>:\n{comment}\n\n"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Add comment", callback_data=f"addcomment_{shop_id_str}"
                ),
                InlineKeyboardButton(
                    text="⬅️ Back", callback_data=f"shop_{shop_id_str}"
                )
            ]
        ])
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logging.error(f"Error fetching comments for shop_{shop_id_str}: {e}")
        await callback.message.answer("error, please try again later.")

@router.callback_query(F.data.startswith("addcomment_"))
async def ask_comment_handler(callback: CallbackQuery, state: FSMContext):
    shop_id_str = callback.data.split("_", 1)[1]
    await state.update_data(shop_id=shop_id_str)
    await callback.message.answer("✏️ Write your comment (max 500 characters):")
    await state.set_state(CommentStates.waiting_for_comment)

@router.message(F.content_type == ContentType.TEXT, CommentStates.waiting_for_comment)
async def save_comment_handler(message: Message, state: FSMContext):
    data        = await state.get_data()
    shop_id     = data.get("shop_id")
    comment_txt = message.text.strip()[:500]
    user        = message.from_user

    if not shop_id:
        await message.answer("❌ Kali Network Core Error")
        await state.clear()
        return

    try:
        await _db.insert_one(
            "comments",
            {
                "shop_id": f"shop_{shop_id}",
                "user_id": user.id,
                "name":    user.full_name,
                "text":    comment_txt,
                "date":    datetime.utcnow().isoformat(),
            },
        )
        await message.answer(
            "✅ Komentārs saglabāts!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ BACK", callback_data=f"shop_{shop_id}")]
            ])
        )
    except Exception as e:
        logging.error(f"Error saving comment: {e}")
        await message.answer("Error DB")
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("shop_"))
async def open_shop(callback: CallbackQuery) -> None:
    shop_id_str = callback.data.split("_", 1)[1]
    try:
        shop = await _db.find_one("shops", {"shop_id": f"shop_{shop_id_str}"})
        if not shop:
            await callback.answer("Shop not found.", show_alert=True)
            return

        votes_count = shop.get("votes", 0)
        about = shop.get("about", "No description available.")
        name = shop.get("name", shop_id_str)
        text = f"{name} ⭐({votes_count})\n\n{about}"

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ VIEW PRODUCTS", callback_data=f"products_{shop_id_str}"
                ),
                InlineKeyboardButton(
                    text="💬 COMMENTS", callback_data=f"comments_{shop_id_str}"
                ),
            ],
            [
                InlineKeyboardButton(text="⬅️ BACK", callback_data="ratings"),
                InlineKeyboardButton(text="⭐ VOTE", callback_data=f"vote_{shop_id_str}"),
            ]
        ])

        await callback.message.answer(text, reply_markup=markup)

    except Exception as e:
        logging.error(f"Error opening shop_{shop_id_str}: {e}")
        await callback.message.answer("❌ Database error, please try again later.")


@router.callback_query(F.data.startswith("vote_"))
async def vote_shop(callback: CallbackQuery) -> None:
    shop_id_str = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id

    try:
        # Check if user already voted 3 times for this shop
        existing_votes = await _db.find(
            "votes",
            {"user_id": user_id, "shop_id": f"shop_{shop_id_str}"},
        )
        if len(existing_votes) >= 3:
            await callback.answer(
                "⚠️ You have already voted 3 times for this shop.", show_alert=True
            )
            return

        # Add vote
        vote_data = {"user_id": user_id, "shop_id": f"shop_{shop_id_str}"}
        await _db.insert_one("votes", vote_data)

        # Update shop votes count
        shop = await _db.find_one("shops", {"shop_id": f"shop_{shop_id_str}"})
        current_votes = shop.get("votes", 0) if shop else 0

        await _db.update_one(
            "shops",
            {"shop_id": f"shop_{shop_id_str}"},
            {"votes": current_votes + 1},
            upsert=True,
        )

        await callback.answer("✅ Your vote has been counted.", show_alert=True)

    except Exception as e:
        logging.error(f"Error voting for shop_{shop_id_str} by user {user_id}: {e}")
        await callback.message.answer("❌ Database error, please try again later.")

@router.message(Command("add_shop"))
async def add_shop_command(message: Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    try:
        existing = await _db.find_one("operators", {"user_id": user_id})
        if existing:
            await message.answer("You are already registered as an operator.")
            return

        new_operator = {"user_id": user_id, "username": username, "votes": 0}
        new_shop = {
            "shop_id": f"shop_{user_id}",
            "owner_id": user_id,
            "name": username,
            "logo_file_id": None,
            "about": "",
            "votes": 0,
        }

        await _db.insert_one("operators", new_operator)
        await _db.insert_one("shops", new_shop)

        await message.answer(
            "✅ You have been added as an operator and now appear in the vote list."
        )

    except Exception as e:
        logging.error(f"Error adding shop for user {user_id}: {e}")
        await message.answer("❌ Database error, please try again later.")

@router.message(Command("admin_votes"))
async def vote_admin_panel(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Access denied.")
        return
    try:
        count = await _db.count_documents("votes")
        await message.answer(f"🗳️ Total votes recorded: {count}")
    except Exception as e:
        logging.error(f"Error fetching vote count: {e}")
        await message.answer("❌ Database error, please try again later.")

# Admin permission to reset operator votes
@router.message(Command("reset_votes"))
async def reset_votes_admin(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Access denied.")
        return
    try:
        await _db.delete_many("votes")
        shops = await _db.find("shops")
        for shop in shops:
            await _db.update_one(
                "shops", {"shop_id": shop["shop_id"]}, {"votes": 0}
            )
        await message.answer("🔄 All votes reset.")
    except Exception as e:
        logging.error(f"Error resetting votes: {e}")
        await message.answer("❌ Database error, please try again later.")

# BACK to ratings
@router.callback_query(F.data == "ratings_back")
async def back_to_ratings(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await show_ratings(callback.message)

# === Show account page ===

async def show_account(message: Message):
    user_id = message.from_user.id
    is_operator = user_id in OPERATOR_IDS

    text = "👤 <b>Your Account</b>\n\n"
    text += f"• ID: <code>{user_id}</code>\n"
    text += f"• Username: @{message.from_user.username or 'Unknown'}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ View your votes", callback_data="view_votes")],
        [InlineKeyboardButton(text="❤️ Shops you like", callback_data="liked_shops")]
    ])

    if is_operator:
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="🛍️ Manage my shop", callback_data="manage_shop")]
        )

    await message.answer(text, reply_markup=kb)

# === Router handler for account button ===
@router.callback_query(F.data == "account")
async def account_return_handler(callback: CallbackQuery):
    await show_account(callback.message)

@router.callback_query(F.data.in_({
    "products_list",
    "shop_tags",
    "shop_owners",
    "shop_link",
    "shop_voters",
    "pause_shop",
    "preview_shop",
    "delete_logo",
    "delete_about",
    "delete_buttons",
    "delete_product",
    "set_buttons",
    "view_votes",
    "liked_shops",
    "soon",
}))
async def placeholder_callback(callback: CallbackQuery):
    await callback.answer("⏳ This feature is coming soon.", show_alert=True)

def create_admin_keyboard() -> InlineKeyboardMarkup:
    """Create admin control keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Reports", callback_data="admin_reports"),
        InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Backup", callback_data="admin_backup"),
        InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")
    )
    return builder.as_markup()
    builder.row(
        InlineKeyboardButton(text="🚨 Report", callback_data=f"report_shop:{shop_id}"),
        InlineKeyboardButton(text="🔙 Back", callback_data="browse_shops")
    )

# === KONFIGURĀCIJA ===
GROUP_ID = -1002320319865  # ← tava grupa
GROUP_LINK = "https://t.me/gg66g6g6"  # ← grupas uzaicinājuma saite

# === POGAS ===
def get_restore_access_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Request Unban", callback_data="request_unban")],
        [InlineKeyboardButton(text="🆘 Priority Support", callback_data="priority_support")],
        [InlineKeyboardButton(text="👑 VIP Upgrade", callback_data="vip_upgrade")],
        [InlineKeyboardButton(text="🎯 EARN CREDITS", callback_data="earn_credits")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="account")]
    ])

@router.callback_query(F.data == "recheck_group")
async def recheck_group_status(callback: CallbackQuery, bot: Bot):
    try:
        member = await bot.get_chat_member(chat_id=GROUP_ID, user_id=callback.from_user.id)
        if member.status in ("member", "administrator", "creator, operator"):
            await callback.answer("✅ You are in the group.", show_alert=True)
        else:
            await callback.answer("❌ You are not a member.", show_alert=True)
    except Exception:
        await callback.answer("⚠️ Error checking group status.", show_alert=True)

def get_earn_credit_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I Invited!", callback_data="check_invites")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="restore_access")]
    ])

# === IEGŪST BALSIS + KREDĪTUS ===
async def get_user_vote_data(user_id: int) -> tuple[int, int]:
    user = await db.find_one("users", {"user_id": user_id})
    votes = await db.find("votes", {"user_id": user_id})
    credits = user.get("credits", 0) if user else 0
    return len(votes), credits

# === RESTORE ACCESS VIEW ===
@router.message(F.text == "🛍️ RESTORE ACCESS")
async def restore_access_entry(message: Message):
    votes_count, credits = await get_user_vote_data(message.from_user.id)

    text = (
        "🔒 <b>Shop Access Restoration</b>\n\n"
        f"✅ Your votes: {votes_count}\n"
        f"🎟️ Restoration credits: {credits}\n\n"
        "💡 <b>Actions:</b>\n"
        "• 🔓 Request unban (5 credits)\n"
        "• 🆘 Priority support (2 credits)\n"
        "• 👑 VIP upgrade (10 credits)\n"
        "• 🎯 Earn credits by inviting users to the group\n"
    )

    await message.answer(text, reply_markup=get_restore_access_buttons(), parse_mode="HTML")

# === EARN CREDITS PAGE ===
@router.callback_query(F.data == "earn_credits")
async def show_earn_credits(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await db.find_one("users", {"user_id": user_id})
    credits = user.get("credits", 0)

    text = (
        "🎯 <b>EARN CREDITS</b>\n\n"
        f"🎟️ Your current credits: <b>{credits}</b>\n\n"
        "📨 Invite your friends to our group to earn 1 credit per 5 invite!\n"
        "✅ Make sure you are in the group first!\n\n"
        "🔗 Group link: " + GROUP_LINK
    )

    await callback.message.edit_text(text, reply_markup=get_earn_credit_buttons(), parse_mode="HTML")

# === CHECK INVITE ===
@router.callback_query(F.data == "check_invites")
async def check_user_invited(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    try:
        member = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        if member.status not in ("member", "administrator", "creator"):
            await callback.answer("❌ You are not in the group.", show_alert=True)
            return
    except Exception:
        await callback.answer("⚠️ Cannot check membership.", show_alert=True)
        return

    user = await db.find_one("users", {"user_id": user_id})
    current = user.get("credits", 0)
    await db.update_one("users", {"user_id": user_id}, {"credits": current + 1})
    await callback.answer("🎉 You earned +1 credit!", show_alert=True)

# === KREDĪTU ATSKAITĪŠANAS FUNKCIJA ===
async def use_credits(user_id: int, amount: int) -> bool:
    user = await db.find_one("users", {"user_id": user_id})
    if not user: return False
    current = user.get("credits", 0)
    if current < amount:
        return False
    await db.update_one("users", {"user_id": user_id}, {"credits": current - amount})
    return True

# === KATRA DARBĪBA ===
@router.callback_query(F.data == "request_unban")
async def handle_unban(callback: CallbackQuery):
    if await use_credits(callback.from_user.id, 5):
        await callback.answer("✅ Unban request submitted!", show_alert=True)
    else:
        await callback.answer("❌ Not enough credits.", show_alert=True)

@router.callback_query(F.data == "priority_support")
async def handle_priority(callback: CallbackQuery):
    if await use_credits(callback.from_user.id, 2):
        await callback.answer("🆘 Priority support activated!", show_alert=True)
    else:
        await callback.answer("❌ Not enough credits.", show_alert=True)

@router.callback_query(F.data == "vip_upgrade")
async def handle_vip(callback: CallbackQuery):
    if await use_credits(callback.from_user.id, 10):
        await callback.answer("👑 VIP upgrade granted!", show_alert=True)
    else:
        await callback.answer("❌ Not enough credits.", show_alert=True)

@router.callback_query(F.data == "restore_access")
async def back_restore(callback: CallbackQuery):
    votes_count, credits = await get_user_vote_data(callback.from_user.id)
    text = (
        "🔒 <b>Shop Access Restoration</b>\n\n"
        f"✅ Your votes: {votes_count}\n"
        f"🎟️ Restoration credits: {credits}\n\n"
        "💡 <b>Actions:</b>\n"
        "• 🔓 Request unban (5 credits)\n"
        "• 🆘 Priority support (2 credits)\n"
        "• 👑 VIP upgrade (10 credits)\n"
        "• 🎯 Earn credits by inviting users to the group\n"
    )
    await callback.message.edit_text(text, reply_markup=get_restore_access_buttons(), parse_mode="HTML")

from datetime import datetime, timedelta

@router.callback_query(F.data == "check_invites")
async def check_user_invited(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    try:
        member = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        if member.status not in ("member", "administrator", "creator"):
            await callback.answer("❌ You are not in the group.", show_alert=True)
            return
    except Exception:
        await callback.answer("⚠️ Cannot check group membership.", show_alert=True)
        return

    user = await db.find_one("users", {"user_id": user_id})
    if not user:
        await callback.answer("⚠️ User not found in database.", show_alert=True)
        return

    last_time_str = user.get("last_invite_time")
    now = datetime.utcnow()

    if last_time_str:
        try:
            last_time = datetime.fromisoformat(last_time_str)
            if now - last_time < timedelta(hours=24):
                await callback.answer("⏳ You can only earn 1 credit per 24 hours.", show_alert=True)
                return
        except Exception:
            pass  # ja ir nepareizs formāts, turpinām

    # ✅ Piešķirt kredītu
    current = user.get("credits", 0)
    await db.update_one("users", {"user_id": user_id}, {
        "credits": current + 1,
        "last_invite_time": now.isoformat()
    })

    await callback.answer("🎉 You earned +1 credit!", show_alert=True)

@router.message(Command("setmedia"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_setmedia_start(m, state):
    await m.answer("Kāda veida fails? (photo / video / gif)")
    await state.set_state(MediaUpload.waiting_kind)

@router.message(MediaUpload.waiting_kind, F.text.lower().in_(["photo","video","gif"]))
async def cmd_setmedia_kind(m, state):
    await state.update_data(kind=m.text.lower())
    await m.answer("Tagad ieraksti atslēgu (key), piemēram: `top_1` vai `welcome`")
    await state.set_state(MediaUpload.waiting_key)

@router.message(MediaUpload.waiting_key, F.text)
async def cmd_setmedia_key(m, state):
    await state.update_data(key=m.text.strip())
    await m.answer("Lūdzu, atsūti tagad pašu failu (photo/video/gif).")
    await state.set_state(MediaUpload.waiting_file)

@router.message(
    MediaUpload.waiting_file,
    lambda msg: msg.photo or msg.video or msg.animation
)
async def cmd_setmedia_file(m, state):
    data = await state.get_data()
    kind = data["kind"]
    key  = data["key"]

    # izvelamies file_id
    if m.photo:
        fid = m.photo[-1].file_id
    elif m.video:
        fid = m.video.file_id
    else:
        fid = m.animation.file_id

    # saglabājam:
    put(kind, key, fid)

    await m.answer(f"✅ Saglabāts `{kind}` → `{key}`")
    await state.clear()

# === Main run ===
async def main() -> None:
    await on_startup()                  # inicializē datubāzi
    await dp.start_polling(bot)        # palaiž polling


    from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, FSInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
)

router = Router()

def get_star_rating(votes: int) -> str:
    """
    Return a string of stars based on votes.
    """
    if votes >= 601:
        return "⭐️⭐️⭐️⭐️⭐️"
    elif votes >= 351:
        return "⭐⭐️⭐️"
    elif votes >= 186:
        return "⭐️⭐️"
    elif votes >= 76:
        return "⭐️⭐️"
    elif votes >= 5:
        return "⭐️"
    else:
        return ""

# ── Page 1 ───────────────────────────────────────────────────────
@router.message(F.text == "⭐️ RATINGS")
async def show_top1(message: Message):
    photo = FSInputFile("Top1.jpg")
    caption = (
        "<b>🗂 Trusted Operators (Kali Network)</b>\n"
        "Kali Network User Vote System\n\n"
        "⭐️ Catalogue contains TOP 1 shops in 18 categories\n\n"
        "1. CHRISTMAS ☃️ RIGA (⭐️) → <a href='https://t.me/knc228_bot?start=90'>catalogue</a>\n"
        "2. ALIEN 👽SUPPLY (⭐️) → <a href='https://t.me/knc228_bot?start=91'>catalogue</a>\n"
        "3. AQUA 🐟 (⭐️) → <a href='https://t.me/knc228_bot?start=92'>catalogue</a>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Next", callback_data="top_2")],
        [InlineKeyboardButton(text="📥 GROUPS", url="https://t.me/knc228_group")]
    ])
    await message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")

# ── Page 2 ───────────────────────────────────────────────────────
@router.callback_query(F.data == "top_2")
async def show_top2(callback: CallbackQuery):
    photo = FSInputFile("Top2.jpg")
    caption = (
        "<b>TOP 2 Catalogue</b>\n\n"
        "⭐️ Catalogue contains TOP 2 shops in 18 categories\n\n"
        "4. FAST 🐇 RABBIT (⭐️) → <a href='https://t.me/knc228_bot?start=93'>catalogue</a>\n"
        "5. Fire Fighter 👨‍🚒 (⭐️) → <a href='https://t.me/knc228_bot?start=94'>catalogue</a>\n"
        "6. PAPAS TEAM ❄️ (⭐️) → <a href='https://t.me/knc228_bot?start=95'>catalogue</a>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Back", callback_data="top_1"),
            InlineKeyboardButton(text="▶️ Next", callback_data="top_3")
        ],
        [InlineKeyboardButton(text="📥 GROUPS", url="https://t.me/knc228_group")]
    ])
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML"),
        reply_markup=kb
    )
    await callback.answer()

# ── Page 3 ───────────────────────────────────────────────────────
@router.callback_query(F.data == "top_3")
async def show_top3(callback: CallbackQuery):
    photo = FSInputFile("Top3.jpg")
    caption = (
        "<b>TOP 3 Catalogue</b>\n\n"
        "⭐️ Catalogue contains TOP 3 shops in 18 categories\n\n"
        "7. CUBA 🇨🇺 OPERATOR (⭐️) → <a href='https://t.me/knc228_bot?start=96'>catalogue</a>\n"
        "8. PURE MAGIC 🧙‍♂️ (⭐️) → <a href='https://t.me/knc228_bot?start=97'>catalogue</a>\n"
        "9. POSTO 🇪🇪 SHOP (⭐️) → <a href='https://t.me/knc228_bot?start=98'>catalogue</a>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Back", callback_data="top_2"),
            InlineKeyboardButton(text="▶️ Next", callback_data="top_4")
        ],
        [InlineKeyboardButton(text="📥 GROUPS", url="https://t.me/knc228_group")]
    ])
    await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ── Page 4 ───────────────────────────────────────────────────────
@router.callback_query(F.data == "top_4")
async def show_top4(callback: CallbackQuery):
    photo = FSInputFile("Top4.jpg")
    caption = (
        "<b>TOP 4 Catalogue</b>\n\n"
        "⭐️ TOP 4 shops in 18 categories\n\n"
        "10. PLUG 💎 WALL•E (⭐️) → <a href='https://t.me/knc228_bot?start=99'>catalogue</a>\n"
        "11. VOZOL VAPES ✅ (⭐️) → <a href='https://t.me/knc228_bot?start=100'>catalogue</a>\n"
        "12. HYDRA (⭐️) → <a href='https://t.me/knc228_bot?start=101'>catalogue</a>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Back", callback_data="top_3"),
            InlineKeyboardButton(text="▶️ Next", callback_data="top_5")
        ],
        [InlineKeyboardButton(text="📥 GROUPS", url="https://t.me/knc228_group")]
    ])
    await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ── Page 5 ───────────────────────────────────────────────────────
@router.callback_query(F.data == "top_5")
async def show_top5(callback: CallbackQuery):
    photo = FSInputFile("Top5.jpg")
    caption = (
        "<b>TOP 5 Catalogue</b>\n\n"
        "⭐️ TOP 5 shops in 18 categories\n\n"
        "13. ARKUS 🥥 (⭐️) → <a href='https://t.me/knc228_bot?start=102'>catalogue</a>\n"
        "14. NarkoTendo 🍄 (⭐️) → <a href='https://t.me/knc228_bot?start=103'>catalogue</a>\n"
        "15. DonII498 🍁 (⭐️) → <a href='https://t.me/knc228_bot?start=104'>catalogue</a>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Back", callback_data="top_4"),
            InlineKeyboardButton(text="▶️ Next", callback_data="top_6")
        ],
        [InlineKeyboardButton(text="📥 GROUPS", url="https://t.me/knc228_group")]
    ])
    await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ── Page 6 ───────────────────────────────────────────────────────
@router.callback_query(F.data == "top_6")
async def show_top6(callback: CallbackQuery):
    photo = FSInputFile("Top6.jpg")
    caption = (
        "<b>TOP 6 Catalogue</b>\n\n"
        "⭐️ TOP 6 shops in 18 categories\n\n"
        "16. CORNER SHOP LV 🐦‍⬛️ (⭐️) → <a href='https://t.me/knc228_bot?start=105'>catalogue</a>\n"
        "17. SOUTHPARK 🥥 (⭐️) → <a href='https://t.me/knc228_bot?start=106'>catalogue</a>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="top_5")],
        [InlineKeyboardButton(text="📥 GROUPS", url="https://t.me/knc228_group")]
    ])
    await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# — 2) helper to build the inline keyboard —
def make_top_kb(prev_id, next_id):
    kb = InlineKeyboardBuilder()
    row = []
    if prev_id:
        row.append(InlineKeyboardButton(text="◀️", callback_data=prev_id))
    if next_id:
        row.append(InlineKeyboardButton(text="▶️", callback_data=next_id))
    # always add a link back to your group or main bot
    row.append(InlineKeyboardButton(text="GROUPS →", url="https://t.me/JoinKali_BOT"))
    kb.row(*row)
    return kb.as_markup()

# — 3) send a TOP page into any chat —
async def send_top_page(idx: int, chat_id: int):
    page = TOP_PAGES[idx]
    await bot.send_photo(
        chat_id=chat_id,
        photo=FSInputFile(page["photo"]),
        caption=page["caption"],
        reply_markup=make_top_kb(page["prev"], page["next"]),
    )

# — 4) callbacks for each “top_n” button —
@router.callback_query(F.data == "top_1")
async def _go1(cq: CallbackQuery):
    await send_top_page(0, cq.message.chat.id)
    await cq.answer()

@router.callback_query(F.data == "top_2")
async def _go2(cq: CallbackQuery):
    await send_top_page(1, cq.message.chat.id)
    await cq.answer()

# … and so on through top_6 …
@router.callback_query(F.data == "top_6")
async def _go6(cq: CallbackQuery):
    await send_top_page(5, cq.message.chat.id)
    await cq.answer()

# — 5) background task to rotate every 30 minutes —
async def recurring_top_worker():
    idx = 0
    await asyncio.sleep(5)   # small startup delay
    while True:
        try:
            await send_top_page(idx, GROUP_CHAT_ID)
        except:
            pass
        idx = (idx + 1) % len(TOP_PAGES)
        await asyncio.sleep(30 * 60)  # 30 minutes

# === Manage Shop Menu  ===
@router.callback_query(F.data == "manage_shop")
async def manage_shop(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📄 PRODUCT LIST", callback_data="products_list")],
        [InlineKeyboardButton("🧩 MAIN PAGE",     callback_data="main_page")],
        [InlineKeyboardButton("🏷 TAGS",          callback_data="shop_tags")],
        [InlineKeyboardButton("👤 OWNERS",        callback_data="shop_owners")],
        [InlineKeyboardButton("🔗 MY SHOP LINK",  callback_data="shop_link")],
        [InlineKeyboardButton("⭐ VOTERS",        callback_data="shop_voters")],
        [InlineKeyboardButton("⛔ PAUSE",         callback_data="pause_shop")],
        [InlineKeyboardButton("⬅️ BACK",          callback_data="account")],
    ])
    await callback.message.edit_text("🛠 Manage your shop using the[B buttons below:", reply_markup=kb)
    await callback.answer()


# === Main Page Settings Menu ===
@router.callback_query(F.data == "main_page")
async def main_page_settings(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("🖼 SET LOGO",    callback_data="set_logo"),
            InlineKeyboardButton("❌ DELETE LOGO", callback_data="delete_logo"),
        ],
        [
            InlineKeyboardButton("📝 SET ABOUT",   callback_data="set_about"),
            InlineKeyboardButton("❌ DELETE ABOUT",callback_data="delete_about"),
        ],
        [
            InlineKeyboardButton("🔘 SET BUTTONS", callback_data="set_buttons"),
            InlineKeyboardButton("❌ DELETE BUTTONS", callback_data="delete_buttons"),
        ],
        [
            InlineKeyboardButton("🗿 ADD PRODUCT",    callback_data="add_product"),
            InlineKeyboardButton("🗑️ DELETE PRODUCT", callback_data="delete_product"),
        ],
        [
            InlineKeyboardButton("▶️ PREVIEW",    callback_data="preview_shop"),
            InlineKeyboardButton("⬅️ BACK",       callback_data="manage_shop"),
        ],
    ])
    await callback.message.edit_text("⚙️ Set up your main page:", reply_markup=kb)
    await callback.answer()


# === PRODUCT LIST ===
@router.callback_query(F.data == "products_list")
async def show_products_list(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    shop_id = f"shop_{user_id}"
    products = await _db.find("products", {"shop_id": shop_id})
    if not products:
        await callback.message.answer("📦 No products yet.")
    else:
        for p in products:
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_product:{p['product_id']}")
            )
            await callback.message.answer_photo(p["photo"], caption=p["description"], reply_markup=kb)
    await callback.answer()


# === TAGS ===
@router.callback_query(F.data == "shop_tags")
async def show_tags(callback: CallbackQuery) -> None:
    shop = await _db.find_one("shops", {"shop_id": f"shop_{callback.from_user.id}"})
    tags = shop.get("tags", "—")
    await callback.message.edit_text(f"🏷 Current tags: {tags}")
    await callback.answer()


# === OWNERS ===
@router.callback_query(F.data == "shop_owners")
async def show_owners(callback: CallbackQuery) -> None:
    # piem., tikai atgriež owner_id
    await callback.message.edit_text(f"👤 Owner: {callback.from_user.full_name} (ID {callback.from_user.id})")
    await callback.answer()


# === MY SHOP LINK ===
@router.callback_query(F.data == "shop_link")
async def show_shop_link(callback: CallbackQuery) -> None:
    link = f"https://t.me/knc228_bot?start={callback.from_user.id}"
    await callback.message.edit_text(f"🔗 Your shop link:\n{link}")
    await callback.answer()


# === VOTERS LIST ===
@router.callback_query(F.data == "shop_voters")
async def show_voters(callback: CallbackQuery) -> None:
    votes = await _db.find("votes", {"shop_id": f"shop_{callback.from_user.id}"})
    voters = ", ".join(str(v["user_id"]) for v in votes) or "No votes yet"
    await callback.message.edit_text(f"⭐ Voters:\n{voters}")
    await callback.answer()


# === PAUSE SHOP ===
@router.callback_query(F.data == "pause_shop")
async def pause_shop(callback: CallbackQuery) -> None:
    await _db.update_one("shops", {"shop_id": f"shop_{callback.from_user.id}"}, {"status": "paused"})
    await callback.message.edit_text("⛔ Shop paused.")
    await callback.answer()


# === PREVIEW SHOP (main page) ===
@router.callback_query(F.data == "preview_shop")
async def preview_shop(callback: CallbackQuery) -> None:
    shop = await _db.find_one("shops", {"shop_id": f"shop_{callback.from_user.id}"})
    text = f"<b>{shop['name']}</b>\n\n{shop.get('about','—')}"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="main_page"))
    if shop.get("logo_file_id"):
        await callback.message.answer_photo(shop["logo_file_id"], caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

async def get_top_operators_page(page: int = 1, page_size: int = 5) -> tuple[str, InlineKeyboardMarkup]:
    offset = (page - 1) * page_size
    top = await _db.get_top_operators(limit=page_size, offset=offset)
    text = f"<b>⭐ TOP operatori — lapa {page}</b>\n\n"
    if not top:
        text += "❌ Nav neviena operatora."
    else:
        for i, (user_id, username, votes) in enumerate(top, start=1 + offset):
        name = f"@{username}" if username else f"ID {user_id}"
            text += f\"{i}. {name} — {votes} ⭐\n\"
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(\"◀️ Iepriekšējā\", callback_data=f\"top_prev:{page-1}\"))
    if len(top) == page_size:
        buttons.append(InlineKeyboardButton(\"Nākamā ▶️\", callback_data=f\"top_next:{page+1}\"))
    kb = InlineKeyboardMarkup().add(*buttons) if buttons else None
    return text, kb

@router.message(F.text == "⭐ RATINGS ⭐")
async def ratings_handler(message: Message):
    text, kb = await get_top_operators_page(page=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("top_prev") | F.data.startswith("top_next"))
async def top_page_callback(query: CallbackQuery):
    action, page_str = query.data.split(":")
    page = int(page_str)
    text, kb = await get_top_operators_page(page=page)
    await query.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await query.answer()

if __name__ == "__main__":
    import asyncio
