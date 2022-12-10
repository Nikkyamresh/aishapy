import sqlite3
"""
con.execute("INSERT INTO admin (ID,pass) \
      VALUES (1, '4ca82782c5372a547c104929f03fe7a9' )")

con.execute("INSERT INTO public (ID,pass) \
      VALUES (2, 'c46335eb267e2e1cde5b017acb4cd799' )")
con.commit()"""
res ="912ec803b2ce49e4a541068d495ab570"
con = sqlite3.connect('database.db')
cus=con.execute("SELECT *  from public")
for row in cus:
      print("old data : "+row[1])
con.execute("UPDATE public set pass=? where id=?",(res,1))
con.commit()
print("totle commit "+str(con.total_changes))
cus=con.execute("SELECT *  from public")
for row in cus:
      print("data after execution : "+row[1])
con.close()
print("database closed")
con=sqlite3.connect('database.db')
print("database re-connected")
cus=con.execute("SELECT *  from public")
for row in cus:
      print("data after re-connection: "+row[1])
con.close()
print("done")
