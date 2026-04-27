# Overstats Curl Examples

```bat
curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-profile" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-profile.json

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-profile/image" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-profile-quick.png

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-match" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-match.json

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-match/image" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-match.png

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-match/detail" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\",\"index\":0}" --output dashen-match-detail.json

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-match/detail/image" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\",\"index\":0}" --output dashen-match-detail.png

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-summary/today" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-summary-today.json

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-summary/today/image" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-summary-today.jpg

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-summary/yesterday" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-summary-yesterday.json

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-summary/yesterday/image" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-summary-yesterday.jpg

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-summary/week" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-summary-week.json

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-summary/week/image" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-summary-week.jpg

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-rank-history" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-rank-history.json

curl.exe -X POST "http://127.0.0.1:18080/api/v2/dashen-rank-history/image" -H "Content-Type: application/json; charset=utf-8" -d "{\"bnet_id\":\"oL1ama#5684\"}" --output dashen-rank-history.png
```
