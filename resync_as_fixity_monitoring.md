# Exploration for use of `resync` in fixity monitoring

## Speed tests

### 2017-03-22 `resync` vs `hashdeep` using SHA-1 on mac laptop

(py3)simeon@RottenApple ~> time hashdeep -c sha1 -r src > /tmp/hd
real  6m37.671s
user  5m58.477s
sys   2m14.868s

(py3)simeon@RottenApple ~> time resync --resourcelist --max-sitemap-entries=9999999999 --outfile=/tmp/a.xml --hash=sha-1 src
Using URI mapping: /Users/simeon/src -> /Users/simeon/src

real  5m44.658s
user  2m45.993s
sys   1m39.271s

(py3)simeon@RottenApple ~> time hashdeep -c sha1 -r src > /tmp/hd

real  6m31.892s
user  5m54.578s
sys   2m14.109s

Speeds about the same. But there are 220k resources in hashdeep inventory, 190k in resync -- why different?