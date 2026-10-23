# Smart Qora — yeni bilgisayarda kurulum

Bu dosya projeyi başka bir Windows bilgisayarda sıfırdan açmak içindir. Adımlar
bir yapay zekâ asistanının (ör. Claude Code) baştan sona kendi başına
uygulayabileceği şekilde yazılmıştır: her adımın ardından bir **kontrol** vardır;
kontrol geçmeden sonraki adıma geçilmez.

Komutlar PowerShell içindir. Her komut ayrı satırda, tek tek çalıştırılır.

---

## 1. Gerekli programlar

| Program | Nereden | Kontrol komutu |
|---|---|---|
| Git | https://git-scm.com/download/win | `git --version` |
| Docker Desktop | https://www.docker.com/products/docker-desktop/ | `docker info` hatasız bitmeli |
| NVIDIA sürücüsü (yalnızca NVIDIA ekran kartı varsa) | https://www.nvidia.com/drivers | `nvidia-smi` ekran kartını göstermeli |

- Docker Desktop kurulduktan sonra **açık** olmalıdır; `docker info` hata verirse Docker Desktop'ı başlatıp bir dakika bekleyin.
- Windows'ta Docker Desktop GPU'yu kendisi kullanır, ayrıca bir şey kurmaya gerek yoktur.

## 2. Projeyi indir

```powershell
git clone https://github.com/RuslanHinizov/Smart-Qora.git
```

```powershell
cd Smart-Qora
```

**Kontrol:** klasörde `docker-compose.yml`, `models/best.pt` ve `videos/crop_23.11.23-12.MP4` bulunmalı.

## 3. GPU yoksa (yalnızca bu durumda)

`nvidia-smi` çalışmıyorsa veya bilgisayarda NVIDIA ekran kartı yoksa,
`docker-compose.yml` içindeki `backend` servisinden şu bloğu **tamamen** silin:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - {driver: nvidia, count: 1, capabilities: [gpu]}
```

Silinmezse backend konteyneri GPU bulamadığı için başlamaz. GPU olmadan sayım
çalışır ama yavaştır.

## 4. Başlat

```powershell
docker compose up -d --build
```

İlk derleme 15–20 dakika sürebilir (PyTorch indiriliyor).

**Kontrol:** şu iki komut beklenen sonucu vermeli (backend'in ayağa kalkması
derlemeden sonra 1–2 dakika sürebilir; sonuç gelene kadar tekrar deneyin):

```powershell
docker compose ps
```

Üç servis (`db`, `backend`, `frontend`) `Up` / `healthy` olmalı.

```powershell
curl.exe -s http://localhost:5173/api/health
```

Beklenen: `{"status":"ok","db":true,"worker":"running"}`

## 5. Aç

Tarayıcıda **http://localhost:5173** adresine gidin.

- Giriş: `admin` / `admin`
- İlk iş: **Ayarlar → Hesap** bölümünden şifreyi değiştirin.

Panelde canlı kamera görüntüsü (demo video) ve sayım görünmelidir.

Varsayılan ayarda demo video **bir kez** sayılır, sonraki tekrarlar yalnızca
önizlemedir; Telegram'a tekrar tekrar mesaj gitmez.

---

## 6. (İsteğe bağlı) Eski bilgisayardaki verileri taşımak

Kullanıcılar, sayım geçmişi, çiftlik envanteri ve Telegram ayarları GitHub'da
**değildir**; eski bilgisayarın Docker veritabanındadır. Taşımak için:

### 6a. Eski bilgisayarda yedek al

Smart-Qora klasöründe:

```powershell
docker compose start db
```

```powershell
docker compose exec db pg_dump -U postgres smart_qora -f /tmp/yedek.sql
```

```powershell
docker compose cp db:/tmp/yedek.sql ./yedek.sql
```

**Kontrol:** klasörde `yedek.sql` oluşmuş ve boş olmamalı.

`yedek.sql` dosyasını (USB veya bulut ile) yeni bilgisayardaki `Smart-Qora`
klasörüne kopyalayın. **Bu dosyayı GitHub'a yüklemeyin**: şifre özetleri ve
Telegram bot token'ı içerir (`.gitignore` bunu zaten engeller).

### 6b. Yeni bilgisayarda geri yükle

4. adım tamamlanmış ve sistem çalışıyor olmalı. Smart-Qora klasöründe:

```powershell
docker compose cp ./yedek.sql db:/tmp/yedek.sql
```

```powershell
docker compose exec db psql -U postgres -c "DROP DATABASE smart_qora WITH (FORCE)" -c "CREATE DATABASE smart_qora"
```

```powershell
docker compose exec db psql -U postgres -d smart_qora -f /tmp/yedek.sql
```

```powershell
docker compose restart backend
```

**Kontrol:** `curl.exe -s http://localhost:5173/api/health` yine
`"status":"ok"` dönmeli. Giriş artık `admin`/`admin` ile **değil**, eski
bilgisayarda kullanılan kullanıcı adı ve şifre ile yapılır.

Not: Telegram ayarları da geri geldiği için bildirimler yeniden başlar.

---

## Sık kullanılan komutlar

| Ne | Komut |
|---|---|
| Durdur (veriler kalır) | `docker compose stop` |
| Yeniden başlat | `docker compose start` |
| Günlükleri izle | `docker compose logs -f backend` |
| Güncelle | `git pull` sonra `docker compose up -d --build` |

`docker compose down -v` **veritabanını siler**; bilerek istenmedikçe kullanmayın.

Daha fazla ayrıntı: [ZAPUSK.md](ZAPUSK.md) (Rusça) ve [README.md](README.md) (İngilizce).
