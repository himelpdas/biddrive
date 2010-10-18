try: config=open('routes.conf','r').read()
except: config=''

def auto_in(apps):
    routes=[
        ('/robots.txt','/welcome/static/robots.txt'),
        ('/favicon.ico','/welcome/static/favicon.ico'),
        ('/admin$a','/admin$a'),
        ]
    for a,b in [x.strip().split() for x in apps.split('\n') if x.strip() and not x.strip().startswith('#')]:
        if not b.startswith('/'): b='/'+b
        if b.endswith('/'): b=b[:-1]
        app = b.split('/')[1]
        routes+=[
            ('.*:https?://(.*\.)?%s:$method /' % a,'%s' % b),
            ('.*:https?://(.*\.)?%s:$method /static/$a' % a,'%s/static/$a' % app),
            ('.*:https?://(.*\.)?%s:$method /appadmin/$a' % a,'%s/appadmin/$a' % app),
            ('.*:https?://(.*\.)?%s:$method /$a' % a,'%s/$a' % b), 
            ]
    return routes

def auto_out(apps):
    routes=[]
    for a,b in [x.strip().split() for x in apps.split('\n') if x.strip() and not x.strip().startswith('#')]:
        if not b.startswith('/'): b='/'+b
        if b.endswith('/'): b=b[:-1]
        app = b.split('/')[1]
        routes+=[
            ('%s/static/$a' % app,'/static/$a'),
            ('%s/appadmin/$a' % app, '/appadmin/$a'),
            ('%s/$a' % b, '/$a'),
            ]
    return routes

routes_in=auto_in(config)
routes_out=auto_out(config)
