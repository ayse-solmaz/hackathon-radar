# 📡 Hackathon Radar

Başvurusu açık **hackathon, ideathon, datathon ve yarışmaları** tek sayfada toplayan, her gün GitHub Actions ile kendini yenileyen statik site.

## Kaynaklar

| Kaynak | Yöntem | Anahtar gerekir mi? |
|---|---|---|
| Devpost | Public JSON API | Hayır |
| MLH | Sayfadaki gömülü JSON | Hayır |
| Luma | Discover API (`hackathon`, `datathon`… araması + İstanbul/Ankara/İzmir) | Hayır |
| Coderspace | JSON-LD | Hayır |
| Techcareer.net | Next.js verisi (`/hackathon`, `/datathon`, `/ideathon`) | Hayır |
| Youthall, Anbean Kampüs | HTML kartları | Hayır |
| Kaggle | Kaggle API | `KAGGLE_USERNAME`, `KAGGLE_KEY` |
| LinkedIn, Instagram, X, TikTok, üniversiteler (edu.tr), Kommunity, GDG, Patika, BTK Akademi, Teknofest, Medium… | Google araması (Serper.dev), son 1 ay, `site:` sorguları | `SERPER_API_KEY` |
| Sosyal gönderilerin ayıklanması | Claude: gerçekten açık bir yarışma mı, adı / son başvuru / düzenleyen | `ANTHROPIC_API_KEY` (opsiyonel) |

Instagram/TikTok/X/LinkedIn doğrudan kazımayı engellediği için bu gönderiler Google indeksinden bulunur. `ANTHROPIC_API_KEY` yoksa anahtar kelime + tarih sezgiseli kullanılır; daha gürültülü olur.

## Kurulum (GitHub)

1. **Settings → Secrets and variables → Actions** altına ekle:
   - `SERPER_API_KEY` — https://serper.dev (ücretsiz 2.500 sorgu; günde ~14 sorgu kullanılır)
   - `ANTHROPIC_API_KEY` — https://console.anthropic.com (opsiyonel)
   - `KAGGLE_USERNAME`, `KAGGLE_KEY` (opsiyonel)
   - Değişken (Variables) `CLAUDE_MODEL` — varsayılan `claude-opus-5-5`; daha ucuz için `claude-haiku-5-5`
2. **Settings → Pages → Source: GitHub Actions**
3. **Actions → Günlük güncelleme ve yayın → Run workflow**

Workflow her gün 07:00'de (TR) çalışır, veriyi `site/data/events.json` olarak commit'ler ve Pages'e yayınlar.

## Yerelde çalıştırma

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m scraper.run
python -m http.server 8765 --directory site
```

## Yeni kaynak eklemek

`scraper/sources.py` içine `list[Event]` döndüren bir fonksiyon yaz ve `ALL` sözlüğüne ekle. Sosyal/web sorguları `scraper/social.py` → `QUERIES`.
