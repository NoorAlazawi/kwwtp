# قالب ملف WSGI لـ PythonAnywhere.
# انسخ محتواه إلى: /var/www/karbalaawwtp_pythonanywhere_com_wsgi.py
# بيانات الاتصال والأسرار تُوضع في ملف .env داخل مجلّد المشروع (لا هنا).
import sys

project_home = "/home/karbalaawwtp/kwwtp"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
