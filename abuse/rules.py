"""Hız sınırı kuralları (ilk değerler). Canlıda 429 sayısına bakılıp ayarlanır; tek yer burası.

CGNAT notu: mobil operatörlerde çok sayıda kullanıcı aynı IP'yi paylaşabilir, bu yüzden oy
sınırları IP'ye tarayıcı bilgisini de katar ve bilerek gevşek tutulur.
"""

from datetime import timedelta

from .limits import Limit

MINUTE = timedelta(minutes=1)
QUARTER_HOUR = timedelta(minutes=15)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)

# Oy (üye veya misafir): IP + tarayıcı başına. Akıştaki 20 anketi hızlıca oylayan gerçek
# kullanıcıya yer bırakır.
VOTE = Limit("vote", ((40, MINUTE), (400, HOUR)))

# Oy için yalnızca IP'ye bağlı tavan. User-Agent'ı istemci belirler; `VOTE` tek başına her istekte
# başlığı değiştiren bir betiğe karşı işlemez. Bu tavan başlıktan bağımsızdır, CGNAT'ta bir IP'yi
# paylaşan birçok kişiye yer bırakacak kadar geniştir.
VOTE_IP = Limit("vote_ip", ((150, MINUTE), (2000, HOUR)))

# Misafir oyu, anket başına (kapsam sonuna anket kimliği eklenir). Çerezi silip aynı ankete tekrar
# oy vermeyi zorlaştırır. Yalnızca BAŞARILI misafir oyları sayılır. Yalnızca IP'ye bağlıdır
# (User-Agent katılmaz: değiştirilerek sınırı sıfırlamak çok kolay olurdu); aynı IP'yi paylaşan
# gerçek kullanıcılar için gevşek tutulur, dolunca "giriş yap" mesajı gösterilir.
GUEST_VOTE_PER_POLL = Limit("guest_vote_poll", ((30, DAY),))

REGISTER = Limit("register", ((10, HOUR),))  # IP başına kayıt denemesi

# IP başına giriş denemesi. Saatlik pencere: tek IP'den çok e-posta, tek parola (parola püskürtme).
LOGIN_IP = Limit("login_ip", ((20, MINUTE), (200, HOUR)))
LOGIN_FAILURE_EMAIL = Limit(
    "login_fail_email", ((10, QUARTER_HOUR),)
)  # e-posta başına BAŞARISIZ deneme

POLL_CREATE = Limit("poll_create", ((10, HOUR),))  # kullanıcı başına BAŞARILI anket
