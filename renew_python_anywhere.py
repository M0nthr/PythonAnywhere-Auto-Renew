import os
import sys
import requests
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# الحصول على الحسابات من متغيرات البيئة
ACCOUNTS_RAW = os.environ.get('PA_ACCOUNTS')

if not ACCOUNTS_RAW:
    print("❌ خطأ: لم يتم العثور على متغير PA_ACCOUNTS.")
    sys.exit(1)

LOGIN_URL = "https://www.pythonanywhere.com/login/"

def send_telegram_report(results):
    token = "8260513380:AAH0oR9SehpePt2DMbzn9i9hBmAQjgCc9MI"
    chat_id = "5561387511"
    
    total = len(results)
    success_count = sum(1 for r in results if r['status'] == 'Success')
    
    # تحديد أيقونة الحالة العامة
    status_icon = "✅" if success_count == total else "⚠️"
    status_text = "نجاح تام" if success_count == total else "نجاح جزئي / فشل"
    
    # بناء التقرير بتنسيق راقٍ ومنظم (عربية فصحى)
    report = f"<b>{status_icon} تقرير التجديد التلقائي لـ PythonAnywhere</b>\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    report += f"<b>📊 الحالة العامة:</b> {status_text}\n"
    report += f"<b>📈 الإحصائيات:</b> <code>{success_count} من {total}</code>\n"
    report += f"<b>⏰ وقت التنفيذ:</b> <code>{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</code>\n\n"
    
    report += "<b>📋 تفاصيل الحسابات:</b>\n"
    for r in results:
        icon = "🟢" if r['status'] == 'Success' else "🔴"
        report += f"• <code>{r['user']}</code> ⮕ {icon} <i>{r['msg']}</i>\n"
        
    report += "\n━━━━━━━━━━━━━━━━━━━━\n"
    report += "🚀 <i>بواسطة المساعد الذكي ماي</i>"
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': report,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        print(f"❌ فشل إرسال تقرير تيليجرام: {e}")

def renew_account(username, password):
    dashboard_url = f"https://www.pythonanywhere.com/user/{username}/webapps/"
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        print(f"\n--- 🔐 معالجة الحساب: {username} ---")
        
        login_page = session.get(LOGIN_URL, timeout=10)
        soup = BeautifulSoup(login_page.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            return "Failed", "خطأ في رموز الصفحة"
        
        payload = {
            'csrfmiddlewaretoken': csrf_token['value'],
            'auth-username': username,
            'auth-password': password,
            'login_view-current_step': 'auth'
        }
        
        response = session.post(LOGIN_URL, data=payload, headers={'Referer': LOGIN_URL}, timeout=10, allow_redirects=True)
        
        if "Log out" not in response.text and "logout" not in response.text.lower():
            return "Failed", "فشل تسجيل الدخول"
        
        time.sleep(1)
        dashboard = session.get(dashboard_url, timeout=10)
        soup = BeautifulSoup(dashboard.content, 'html.parser')
        
        forms = soup.find_all('form', action=True)
        extend_action = next((f.get('action') for f in forms if "/extend" in f.get('action', '').lower()), None)
        
        if not extend_action:
            return "Success", "مجدد مسبقاً"
        
        dashboard_csrf = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        extend_url = f"https://www.pythonanywhere.com{extend_action}"
        
        result = session.post(extend_url, data={'csrfmiddlewaretoken': dashboard_csrf['value']}, headers={'Referer': dashboard_url}, timeout=10)
        
        if result.status_code == 200 and "webapps" in result.url.lower():
            return "Success", "تم التجديد بنجاح"
        else:
            return "Failed", f"خطأ: {result.status_code}"
            
    except Exception as e:
        return "Failed", f"خطأ تقني: {str(e)}"

if __name__ == "__main__":
    account_list = [acc.split(':') for acc in ACCOUNTS_RAW.split(',') if ':' in acc]
    results_list = []
    
    total = len(account_list)
    success_count = 0
    
    print(f"🚀 بدء عملية التجديد لـ {total} حسابات...")
    
    for user, pw in account_list:
        u, p = user.strip(), pw.strip()
        status, msg = renew_account(u, p)
        if status == "Success":
            success_count += 1
        results_list.append({'user': u, 'status': status, 'msg': msg})

    # إرسال التقرير النهائي (results_list تم تعريفها الآن!)
    send_telegram_report(results_list)
            
    print("\n" + "="*30)
    print(f"📊 الخلاصة النهائية:")
    print(f"✅ ناجح: {success_count}/{total}")
    print(f"❌ فاشل: {total - success_count}/{total}")
    print("="*30)
    
    sys.exit(0 if success_count == total else 1)
