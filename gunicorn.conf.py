bind = "0.0.0.0:8080"
workers = 2
threads = 4
timeout = 300
graceful_timeout = 30

# SakuraFrp can send contradictory X-Forwarded-* scheme headers for HTTPS
# tunnels. The panel does not need proxy-derived scheme detection, so ignore
# those headers instead of letting gunicorn reject the request.
forwarded_allow_ips = ""
