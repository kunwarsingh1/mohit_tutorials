from flask import Flask, request

app = Flask(__name__)



@app.route('/hello',methods=['GET'])
def mohit():
    return "hellos mohit"


@app.route('/mohit',methods=["POST"])
def posting():
    return "hello "+str(request.json.get('names'))


if __name__=="__main__":
    app.run(host="localhost",port=9000,debug=True)