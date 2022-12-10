from flask import Flask, jsonify, render_template, request
import sqlite3
app = Flask(__name__)
import aisha
import os
import hashlib
def encd(psd):
    return hashlib.md5(psd.encode()).hexdigest()
#os.chdir('aimlfiles')
class Getpssd:
    def adminpsd():
        con = sqlite3.connect('database.db')
        cos=con.execute("SELECT pass FROM admin")
        for row in cos:
            res = row[0]
        con.close()
        return res
    def getpsd():
        con = sqlite3.connect('database.db')
        cosp=con.execute("SELECT pass FROM public")
        for row in cosp:
            res= row[0]
        con.close()
        return res
mybot = aisha.Kernel()
#mybot.learn('aimlfiles/startup.xml')
mybot.bootstrap(brainFile = "bot_brain.brn")
def login(psd):
    if psd==Getpssd.getpsd():
        return True
    else:
        return False
def admin_login(psd):
    if psd==Getpssd.adminpsd():
        return True
    else:
        return False
@app.route('/bot')
def add_numbers():
    a = request.args.get('a', 0, type=str)
    res = mybot.respond(a)
    file = open("static/log.pass.txt","a")
    file.write("me :")
    file.write(a)
    file.write("\nAI :")
    file.write(res)
    file.write("\n")
    file.close()
    mybot.saveBrain("bot_brain.brn")
    return jsonify(result=res)
@app.route('/cpss')
def change_pass():
    filen="aisha/__pycache__/Kernel.cpython-36.pyc"
    if os.path.exists(filen):
        os.remove(filen)
    npsd = request.args.get('npsd', 0, type=str)
    res = encd(npsd)
    con = sqlite3.connect('database.db')
    con.execute("UPDATE public set pass=? where id=?",(res,1))
    con.commit()
    con.close()
    if os.path.exists(filen):
        os.remove(filen)
    return jsonify(result=res)
@app.route('/auth')
def auth():
    a = request.args.get('psd', 0, type=str)
    res = login(a)
    admin = admin_login(a)
    if res==True:
        file = open("static/log.pass.txt","a")
        file.write("\nnew login \n")
        file.close()
        return render_template('index.html')
    else:
        if admin==True:
            file = open("static/log.pass.txt","a")
            file.write("\nnew admin login \n")
            file.close()
            return render_template("admin.html")
        else:
            file = open("static/log.pass.txt","a")
            file.write("\nnew fucm login \n")
            file.close()
            return render_template('auth.html')

@app.route('/')
def index():
    file = open("static/log.pass.txt","a")
    file.write("\nnew new login \n")
    file.close()
    return render_template("auth.html")
if __name__=="__main__":
    app.run()
