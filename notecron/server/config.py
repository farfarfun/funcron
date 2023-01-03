import gevent.monkey

gevent.monkey.patch_all()
bind = '0.0.0.0:8445'
workers = 2
worker_class = 'gevent'
x_forwarded_for_header = 'X-FORWARDED-FOR'
