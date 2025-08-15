from flask import Flask, render_template, request

app = Flask(__name__)

count = [
    {'id': 0, 'name': '中秋节', 'num': 0},
    {'id': 1, 'name': '国庆节', 'num': 0},
    {'id': 2, 'name': '春节', 'num': 0},
    {'id': 3, 'name': '端午节', 'num': 0},
    {'id': 4, 'name': '七夕节', 'num': 0},
    {'id': 5, 'name': '圣诞节', 'num': 0},
]

@app.route('/')
def index():
    return render_template('index_2.html', count=count)

@app.route('/dianzan')
def add():
    id = int(request.args.get('id'))
    cancel = request.args.get('cancel', '0')
    
    for item in count:
        if item['id'] == id:
            if cancel == '1':  # 取消点赞
                item['num'] = max(0, item['num'] - 1)
            elif cancel == '2':  # 清零
                item['num'] = 0
            elif cancel == '3':  # 全部清零
                for i in count:
                    i['num'] = 0
            else:  # 正常点赞
                item['num'] += 1
            break
    
    return render_template('index_3.html', count=count)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)