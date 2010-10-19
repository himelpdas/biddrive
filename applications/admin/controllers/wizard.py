# -*- coding: utf-8 -*- 

if DEMO_MODE:
    response.flash = T('disabled in demo mode')
    redirect(URL('default','site'))

if not session.app:
    session.app={
        'params':[('name','app'),
                  ('title','My First App'),
                  ('subtitle','it rocks'),
                  ('author','you'),
                  ('author','you@example.com'),
                  ('email_server','localhost'),
                  ('email_sender','you@example.com'),
                  ('email_login',''),
                  ('login_method','local'),
                  ('login_config',''),
                  ('layout_theme','')],
        'tables':['auth_user'],
        'table_auth_user':['username','first_name','last_name','email','password'],
        'pages':['index'],
        'page_index':['# welcome to my first app']
        }

THEMES=['one','two','three']

def listify(x):
    if not isinstance(x,(list,tuple)):
        return x and [x] or []
    return x

def clean(name):
    import re
    return re.sub('\W+','_',name.strip().lower())

def index():
    redirect(URL('step1'))

def step1():    
    import os
    response.view='wizard/step.html'
    apps=os.listdir(os.path.join(request.folder,'..'))
    params = dict(session.app['params'])
    form=SQLFORM.factory(Field('name',
                               requires=(IS_ALPHANUMERIC(),
                                         IS_EXPR('not value in %s'%apps,
                                                 error_message='exists')),
                               default=params.get('name',None)),
                         Field('title',default=params.get('title',None)),
                         Field('subtitle',default=params.get('subtitle',None)),
                         Field('author',default=params.get('author',None)),
                         Field('author_email',default=params.get('author_email',None)),
                         Field('email_server',default=params.get('email_server',None)),
                         Field('email_sender',default=params.get('email_sender',None)),
                         Field('email_login',default=params.get('email_login',None)),
                         Field('login_method',requires=IS_IN_SET(('local','cas','rpx')),
                               default=params.get('login_method','local')),
                         Field('login_config',default=params.get('login_config',None)),
                         Field('layout_theme',requires=IS_IN_SET(THEMES),
                               default=params.get('layout_theme',THEMES[0])))
    if form.accepts(request.vars):
        session.app['params']=[(key,form.vars.get(key,None)) 
                               for key,value in session.app['params']]
        redirect(URL('step2'))
    return dict(step='1',form=form)
        
def step2():  
    response.view='wizard/step.html'
    form=SQLFORM.factory(Field('table_names','list:string',
                               default=session.app['tables']))
    if form.accepts(request.vars):
        session.app['tables']=[clean(t)
                               for t in listify(form.vars.table_names)
                               if t.strip()]
        for table in session.app['tables']:
            if not table=='auth_user':
                for key in ['create','read','update','search']:
                    name = table+'_'+key
                    if not name in session.app['pages']:
                        session.app['pages'].append(name)
                        session.app['page_name']=['# %s %s' % (key,table)]
        if session.app['tables']:
            redirect(URL('step3',args=0))
        else:
            redirect(URL('step4'))
    return dict(step='2',form=form)

def step3():
    response.view='wizard/step.html'
    n=int(request.args(0) or 0)
    m=len(session.app['tables'])
    if n>=m: redirect(URL('step2'))
    table=session.app['tables'][n]
    form=SQLFORM.factory(Field('field_names','list:string',
                               default=session.app.get('table_%s'%table,[])))
    if form.accepts(request.vars) and form.vars.field_names:        
        fields=listify(form.vars.field_names)
        if table=='auth_user':
            for field in ['first_name','last_name','email','password']:
                if not field in fields:
                    fields.append(field)
        session.app['table_%s'%table]=[t.strip().lower()
                                       for t in listify(form.vars.field_names)
                                       if t.strip()]
        if n<m-1:
            redirect(URL('step3',args=n+1))
        else:
            redirect(URL('step4'))
    return dict(step='3 (%s of %s)' %(n+1,m),table=table,form=form)

def step4():
    response.view='wizard/step.html'
    form=SQLFORM.factory(Field('pages','list:string',
                               default=session.app['pages']))
    if form.accepts(request.vars):
        session.app['pages']=[clean(t)
                              for t in listify(form.vars.pages)
                              if t.strip()]        
        if session.app['pages']:
            redirect(URL('step5',args=0))
        else:
            redirect(URL('step6'))
    return dict(step='4',form=form)

def step5():
    response.view='wizard/step.html'
    n=int(request.args(0) or 0)
    m=len(session.app['pages'])
    if n>=m: redirect(URL('step4'))
    page=session.app['pages'][n]
    markmin_url='http://web2py.com/examples/static/markmin.html'
    form=SQLFORM.factory(Field('objects','list:string',
                               default=session.app.get('page_%s'%page,[]),
                               comment=A('use markmin',_href=markmin_url,_target='_blank')))
    if form.accepts(request.vars) and form.vars.objects:
        session.app['page_%s' % page]=[t.strip().lower()
                                       for t in listify(form.vars.objects)
                                       if t.strip()] 
        if n<m-1:
            redirect(URL('step5',args=n+1))
        else:
            redirect(URL('step6'))
    return dict(step='5 (%s of %s)' % (n+1,m),form=form)

def step6():
    response.view='wizard/step.html'
    form=FORM(INPUT(_type='submit',_value='generate!'))
    if form.accepts(request.vars):
        redirect(URL('create'))
    return dict(step='6',form=form)

def make_table(file,table,fields):
    file.write('\n'+'#'*40+'\n')
    file.write("db.define_table('%s',\n" % table)
    file.write("    Field('id','id',\n")
    file.write("          represent=lambda id:A('view',_href=URL('%s_read',args=id))),\n"%table)
    first_field=None
    for field in fields:
        items=[x.lower() for x in field.split()]
        has={}
        for key in ['notnull','unique','integer','double','boolean','float','boolean',
                    'date','time','datetime','text','wiki','html','file','upload','true',
                    'hidden','readonly']:
            if key in items:
                has[key]=True
                items = [x for x in items if not x==key]                    
        name = '_'.join(items)
        if not first_field: first_field=name
        type='string'
        for key in ['integer','double','boolean','float','boolean',
                    'date','time','datetime','text','file']:
            if key in has:
                type=key
        if 'wiki' in has or 'html' in has:
            type='text'
        if 'file' in has:
            type='upload'
        for key in items:
            if key in session.app['tables']:
                type='reference %s' % key
                break
        file.write("    Field('%s', type='%s'" % (name, type))
        if 'notnull' in has:
            file.write(', notnull=True')
        if 'unique' in has:
            file.write(', unique=True')
        if type=='boolean' and 'true' in has:
            file.write(",\n          default=True")
        if 'wiki' in has:
            file.write(",\n          represent=lambda x: MARKMIN(x)")
        elif 'html' in has:
            file.write(",\n          represent=lambda x: XML(x,sanitize=True)")
        if 'hidden' in has:
            file.write(",\n          writable=False, readable=False")
        elif 'readonly' in has:
            file.write(",\n          writable=False")
        file.write(",\n          label=T('%s')),\n" % \
                       ' '.join(x.capitalize() for x in name.split('_')))
    if not table=='auth_user' and 'auth_user' in session.app['tables']:
        file.write("    Field('created_on','datetime',default=request.now,\n")
        file.write("          writable=False,readable=False),\n")
        file.write("    Field('created_by',db.auth_user,default=auth.user_id,\n")
        file.write("          writable=False,readable=False),\n")
        file.write("    Field('modified_on','datetime',default=request.now,\n")
        file.write("          writable=False,readable=False,update=request.now),\n")
        file.write("    Field('modified_by',db.auth_user,default=auth.user_id,\n")
        file.write("          writable=False,readable=False,update=auth.user_id),\n")
    file.write("    format='%("+first_field+")s',\n")
    file.write("    migrate=settings.migrate)\n\n")

def make_page(file,page,contents):
    file.write("def %s():\n" % page)
    items=page.rsplit('_',1)
    if items[0] in session.app['tables'] and len(items)==2:
        t=items[0]
        if items[1]=='read':
            file.write("    record = db.%s(request.args(0)) or redirect(URL('error'))\n" % t)
            file.write("    form=crud.read(db.%s,record)\n" % t)
            file.write("    return dict(form=form)\n\n")
        elif items[1]=='update':
            file.write("    record = db.%s(request.args(0)) or redirect(URL('error'))\n" % t)
            file.write("    form=crud.update(db.%s,record,next='%s_read/[id]')\n" % (t,t))
            file.write("    return dict(form=form)\n\n")
        elif items[1]=='create':
            file.write("    form=crud.create(db.%s,next='%s_read/[id]')\n" % (t,t))
            file.write("    return dict(form=form)\n\n")
        elif items[1]=='search':
            file.write("    form, rows=crud.search(db.%s)\n" % t)
            file.write("    return dict(form=form, rows=rows)\n\n")
        else:
            t=None
    else:
        t=None
    if not t:
        file.write("    return dict()\n\n")

def make_view(file,page,contents):
    file.write("{{extend 'layout.html'}}\n\n")
    file.write(str(MARKMIN('\n'.join(contents))))
    items=page.rsplit('_',1)
    if items[0] in session.app['tables'] and len(items)==2:
        t=items[0]
        if items[1] in ('read', 'update' ,'create'):
            file.write('\n{{=form}}\n')
        elif items[1]=='search':
            file.write('\n{{=form}}\n')
            file.write('\n{{=rows}}\n')

def create():
    import os
    from gluon.admin import app_create
    params = dict(session.app['params'])
    app = params['name']
    try: app_create(app,request)
    except: pass
    model = os.path.join(request.folder,'..',app,'models','0.py')
    file = open(model,'wb')
    file.write("from gluon.storage import Storage\n")
    file.write("settings = Storage()\n\n")
    file.write("settings.migrate = True\n")
    for key,value in session.app['params']:
        file.write("settings.%s = '%s'\n" % (key,value))
    file.write('response.title = settings.title\n')
    file.write('response.subtitle = settings.subtitle\n')
    file.close()
    model = os.path.join(request.folder,'..',app,'models','db_wizard.py')
    file = open(model,'wb')
    for table in session.app['tables']:
        if table=='auth_user': continue
        make_table(file,table,session.app['table_'+table])    
    file.close()
    controller = os.path.join(request.folder,'..',app,'controllers','default.py')
    file = open(controller,'wb')
    file.write("""# -*- coding: utf-8 -*- 
def user(): return dict(form=auth())
def download(): return response.download(request,db)
def call():
    session.forget()
    return service()

""")
    for page in session.app['pages']:
        make_page(file,page,session.app.get('page_'+page,[]))
    file.close()
    for page in session.app['pages']:
        view = os.path.join(request.folder,'..',app,'views','default',page+'.html')
        file = open(view,'wb')
        make_view(file,page,session.app.get('page_'+page,[]))
        file.close()
    redirect(URL(params['name'],'default','index'))

