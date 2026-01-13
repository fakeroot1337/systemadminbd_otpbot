from dbase import *

def main():
    # 1. Check if admin exists
    adminid = 1631961416  # Your admin ID
    if check_admin(adminid):
        print(f"✅ Admin {adminid} already exists")
    else:
        try:
            create_admin(adminid)
            create_user_lifetime(adminid)
            print(f"✅ Admin {adminid} created successfully")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # 2. Fetch and display all user data
    print("\n📊 All User Data:")
    users = fetch_UserData_table()
    if users:
        for user in users:
            print(f"User ID: {user[0]}, Phone: {user[2]}, Expiry: {user[11]}")
    else:
        print("No users found")
    
    # 3. Additional checks
    print("\n🔍 Quick Checks:")
    print(f"Total Admins: {len(adminid_fetcher())}")
    print(f"Total Users: {len(userid_fetcher())}")

if __name__ == '__main__':
    main()