import time
from django.contrib.auth import get_user_model
from queue_system.models import Queue
from notifications.sms_service import send_token_sms
from notifications.models import AdminSMSLog

User = get_user_model()
admin = User.objects.filter(is_staff=True).first()
if not admin:
    admin = User.objects.create_user(username='testadmin', password='TestPass123')
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    print('Created admin user:', admin.username)
else:
    print('Using admin user:', admin.username)

# Find a queue whose user has a 10-digit phone; if none, set phone for the first queue's user
q = Queue.objects.filter(user__isnull=False).first()
if not q:
    raise SystemExit('No queues with users found to test')
user = q.user
phone = getattr(user, 'phone_number', '') or getattr(user, 'phone', '')
if not (phone and phone.isdigit() and len(phone) == 10):
    print('User phone invalid or missing for user', user.username, '-> setting phone_number to 8446042386')
    user.phone_number = '8446042386'
    user.save(update_fields=['phone_number'])

# Now run send_token_sms
message = 'Test: Admin manual SMS for token %s at %s' % (q.token_number, q.service.name)
print('Calling send_token_sms for queue id', q.id, 'message:', message)
log = None
try:
    log = send_token_sms(q, message, sent_by_admin_user=admin)
    print('Created AdminSMSLog id', log.id)
except Exception as e:
    print('send_token_sms raised:', repr(e))

# Wait for background worker to update
time.sleep(4)
if log:
    log.refresh_from_db()
    print('AdminSMSLog: id=', log.id, 'success=', log.success)
    print('phone=', log.phone_number)
    print('details=', (log.details or '')[:1000])
else:
    # print latest AdminSMSLog
    last = AdminSMSLog.objects.order_by('-sent_at').first()
    print('Latest AdminSMSLog:', last and (last.id, last.success, last.details) or 'none')
