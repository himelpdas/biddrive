"""
Usage:

   python web2py.py -S app -M -N -R scripts/cpdb.py -A 'sqlite://other_db.sqlite'

this will copy all data from current db to other_db (sqlite or not)

"""
import sys, os

def main():
    other_db = DAL(sys.argv[1])
    print 'creating tables...'
    for table in db:
        other_db.define_table(table._tablename,*[field for field in table])
        other_db[table._tablename].truncate()
    print 'exporting data...'
    db.export_to_csv_file(open('tmp.sql','wb'))
    print 'importing data...'
    other_db.import_from_csv_file(open('tmp.sql','rb'))
    other_db.commit()
    print 'done!'
    print 'Attention: do not run this program again or you end up with duplicate records'

if __name__=='__main__': main()
    
