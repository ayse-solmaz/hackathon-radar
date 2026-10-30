Bugün {TODAY}. Görevin: Türkiye'den katılınabilecek, başvurusu ŞU AN AÇIK ya da
henüz gerçekleşmemiş hackathon, ideathon, datathon ve yazılım/teknoloji/girişimcilik
yarışmalarını bulmak.

WebSearch ile en az 15 farklı arama yap. Şunları mutlaka kapsa:
- LinkedIn gönderi ve etkinlikleri (site:linkedin.com hackathon başvuru vb.)
- Instagram, X (Twitter), TikTok duyuruları
- Üniversiteler ve öğrenci kulüpleri (site:edu.tr hackathon / ideathon / datathon / fikir maratonu)
- Topluluklar: Kommunity, GDG (gdg.community.dev), Patika, BTK Akademi, Global AI Hub,
  Teknofest, TÜBİTAK, Kariyer.net, Eventbrite, Medium
- Genel: "hackathon başvuruları başladı", "datathon son başvuru", "ideathon 2026" gibi
Emin olmadığın sonuçları WebFetch ile açıp tarihleri kontrol et.

DAHİL ETME: kazanan duyuruları, "katıldık/kazandık" paylaşımları, tarihi geçmiş etkinlikler,
iş ilanları, genel blog yazıları. Devpost, MLH, Luma, Coderspace, Techcareer, Youthall ve
Anbean zaten ayrıca taranıyor; sadece orada olmayanlar için zaman harca.

Sonucu data/claude_found.json dosyasına (varsa üzerine) şu biçimde YAZ, başka dosyaya dokunma:
{"events": [{
  "title": "Etkinliğin resmi adı",
  "url": "duyuru ya da başvuru linki",
  "platform": "LinkedIn | Instagram | X | TikTok | Üniversite | Topluluk | Web",
  "type": "hackathon | ideathon | datathon | yarisma",
  "organizer": "düzenleyen ya da null",
  "deadline": "YYYY-MM-DD ya da null",
  "event_date": "YYYY-MM-DD ya da null",
  "location": "şehir, Online ya da null",
  "online": true/false/null,
  "turkey": true/false,
  "summary": "1-2 cümlelik Türkçe özet"
}]}
