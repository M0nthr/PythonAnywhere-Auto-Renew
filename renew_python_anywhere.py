import os
import sys
import requests
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get accounts from environment variable
# Format expected: "user1:pass1,user2:pass2"
ACCOUNTS_RAW = os.environ.get('PA_ACCOUNTS')

if not ACCOUNTS_RAW:
    print("❌ Error: PA_ACCOUNTS environment variable not found.")
    print("   Please set PA_ACCOUNTS in GitHub Secrets as 'user1:pass1,user2:pass2'")
    sys.exit(1)

LOGIN_URL = "https://www.pythonanywhere.com/login/"

def renew_account(username, password):
    dashboard_url = f"https://www.pythonanywhere.com/user/{username}/webapps/"
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        print(f"\n--- 🔐 Processing Account: {username} ---")
        
        # 1. Get login page
        login_page = session.get(LOGIN_URL, timeout=10)
        login_page.raise_for_status()
        
        soup = BeautifulSoup(login_page.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            print(f"❌ [{username}] Could not find CSRF token on login page")
            return False
        
        # 2. Submit login
        payload = {
            'csrfmiddlewaretoken': csrf_token['value'],
            'auth-username': username,
            'auth-password': password,
            'login_view-current_step': 'auth'
        }
        
        response = session.post(
            LOGIN_URL, 
            data=payload, 
            headers={'Referer': LOGIN_URL},
            timeout=10,
            allow_redirects=True
        )
        
        if "Log out" not in response.text and "logout" not in response.text.lower():
            print(f"❌ [{username}] Login failed")
            return False
        
        print(f"✅ [{username}] Login successful")
        
        # 3. Access dashboard
        time.sleep(1)
        dashboard = session.get(dashboard_url, timeout=10)
        dashboard.raise_for_status()
        soup = BeautifulSoup(dashboard.content, 'html.parser')
        
        # 4. Find extend button
        forms = soup.find_all('form', action=True)
        extend_action = next((f.get('action') for f in forms if "/extend" in f.get('action', '').lower()), None)
        
        if not extend_action:
            print(f"ℹ️  [{username}] No extend button found (Not needed yet).")
            return True
        
        # 5. Get CSRF token and submit extend request
        dashboard_csrf = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        extend_url = f"https://www.pythonanywhere.com{extend_action}"
        
        result = session.post(
            extend_url,
            data={'csrfmiddlewaretoken': dashboard_csrf['value']},
            headers={'Referer': dashboard_url},
            timeout=10
        )
        
        if result.status_code == 200 and "webapps" in result.url.lower():
            print(f"✨ [{username}] Web app extended successfully!")
                        return True
        else:
            print(f"⚠️  [{username}] Extension might have failed. Status: {result.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ [{username}] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Parse accounts
    account_list = [acc.split(':') for acc in ACCOUNTS_RAW.split(',') if ':' in acc]
    
    total = len(account_list)
    success_count = 0
    
    print(f"🚀 Starting Auto-Renew for {total} accounts...")
    
    for user, pw in account_list:
        if renew_account(user.strip(), pw.strip()):
            success_count += 1
            
    print("\n" + "="*30)
    print(f"📊 FINAL SUMMARY:")
    print(f"✅ Success: {success_count}/{total}")
    print(f"❌ Failed: {total - success_count}/{total}")
    print("="*30)
    
    sys.exit(0 if success_count == total else 1)
