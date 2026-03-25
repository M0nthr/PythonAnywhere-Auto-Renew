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
    if success_count == total:
        status_icon, status_text = "✅", "نجاح تام"
    elif success_count > 0:
        status_icon, status_text = "⚠️", "نجاح جزئي"
    else:
        status_icon, status_text = "❌", "فشل التجديد"
    
    # بناء التقرير بتنسيق راقٍ ومنظم
    report = f"{status_icon} تقرير التجديد التلقائي لـ PythonAnywhere\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    report += f"📊 ملخص الحالة: {status_text}\n"
    report += f"📈 الإحصائيات: {success_count} من {total}\n"
    report += f"⏰ وقت التنفيذ: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
    
    report += "📋 تفاصيل الحسابات:\n"
    for r in results:
        icon = "🟢" if r['status'] == 'Success' else "🔴"
        report += f"• {r['user']} ⮕ {icon} {r['msg']}\n"
        
    report += "\n━━━━━━━━━━━━━━━━━━━━\n"
    report += "🚀 تمت الإدارة بواسطة ماي"
        
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
        # 1. تسجيل الدخول
        login_page = session.get(LOGIN_URL, timeout=15)
        soup = BeautifulSoup(login_page.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            return "Failed", "خطأ في صفحة الدخول"
        
        payload = {
            'csrfmiddlewaretoken': csrf_token['value'],
            'auth-username': username,
            'auth-password': password,
            'login_view-current_step': 'auth'
        }
        
        response = session.post(LOGIN_URL, data=payload, headers={'Referer': LOGIN_URL}, timeout=15, allow_redirects=True)
        
        if "Log out" not in response.text and "logout" not in response.text.lower():
            return "Failed", "فشل في تسجيل الدخول"
        
        # 2. فحص لوحة التحكم
        time.sleep(2)
        dashboard = session.get(dashboard_url, timeout=15)
        soup = BeautifulSoup(dashboard.content, 'html.parser')
        
        forms = soup.find_all('form', action=True)
        extend_action = next((f.get('action') for f in forms if "/extend" in f.get('action', '').lower()), None)
        
        if not extend_action:
            return "Success", "مجدد مسبقاً"
        
        # 3. الضغط على زر التمديد
        dashboard_csrf = soup.find('input', {'name': 'csrfmiddlewaretoken'})
                extend_url = f"https://www.pythonanywhere.com{extend_action}"
        
        result = session.post(
            extend_url,
            data={'csrfmiddlewaretoken': dashboard_csrf['value']},
            headers={'Referer': dashboard_url},
            timeout=15
        )
        
        if result.status_code == 200 and "webapps" in result.url.lower():
            return "Success", "تم التجديد بنجاح"
        else:
            return "Failed", f"خطأ برقم {result.status_code}"
            
    except Exception as e:
        return "Failed", "خطأ في الاتصال"

if __name__ == "__main__":
    account_list = [acc.split(':') for acc in ACCOUNTS_RAW.split(',') if ':' in acc]
    final_results = []
    
    print(f"🚀 بدء عملية التجديد التلقائي لـ {len(account_list)} حسابات...")
    
    for user, pw in account_list:
        u, p = user.strip(), pw.strip()
        status, msg = renew_account(u, p)
        final_results.append({'user': u, 'status': status, 'msg': msg})
        print(f"[{u}]: {status} - {msg}")
            
    # إرسال التقرير النهائي الأنيق
    send_telegram_report(final_results)
    
    sys.exit(0 if all(r['status'] == 'Success' for r in final_results) else 1)
