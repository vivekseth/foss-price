import random
import string
import requests
import secrets
import locale
from flask import Flask, request, make_response, render_template, send_from_directory

## Globals

app = Flask(__name__)

locale.setlocale( locale.LC_ALL, '')

repo_list = ['https://github.com/ParsePlatform/parse-server',
'https://github.com/mongodb/mongo',
'https://github.com/mitsuhiko/flask',
'https://github.com/mysql/mysql-server',
'https://github.com/apple/swift',
'https://github.com/django/django',
'https://github.com/nodejs/node',
'https://github.com/AFNetworking/AFNetworking',
'https://github.com/Homebrew/homebrew',
'https://github.com/git/git',
'https://github.com/torvalds/linux']

## Helper Functions

def random_state():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

def authorization_url(client_id, redirect_uri, scope, state):
    url = 'https://github.com/login/oauth/authorize?client_id='+client_id + \
        '&redirect_uri='+redirect_uri+ \
        '&scope='+scope + \
        '&state='+state
    return url

def temp_code_to_access_code(client_id, client_secret, code, redirect_uri, state):
    url = 'https://github.com/login/oauth/access_token'
    headers = {'Accept': 'application/json'}
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri,
        'state': state
    }
    r = requests.post(url, headers=headers, data=data)
    return r

def repo_stat_endpoint(repo_path):
	endpoint = '/repos/' + repo_path + '/stats/code_frequency'
	return endpoint

def api_request(token, endpoint):
	headers = {
		'Accept': 'application/vnd.github.v3+json',
		'Authorization': 'token ' + token
	}
	base_url = 'https://api.github.com'
	r = requests.get(base_url + endpoint, headers=headers)
	return r

def repo_stat(json):
	total_additions = reduce(lambda x, y: x+y, map(lambda x: x[1], json), 0)

	char_per_addition = 40 # (1/2) * 80 char per line
	char_per_word = 5 # https://en.wikipedia.org/wiki/Words_per_minute
	wpm_comp = 19 # https://en.wikipedia.org/wiki/Words_per_minute
	salary_per_hour = 45.187 # https://www.glassdoor.com/Salaries/software-engineer-salary-SRCH_KO0,17.htm

	total_hours = (total_additions * char_per_addition) / (wpm_comp * char_per_word * 60)
	total_compensation = salary_per_hour * total_hours

	data = {'hours': total_hours,'cost': total_compensation}
	return data

## Routes

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('templates', path)

@app.route('/', methods=['GET'])
def main_page():
	access_token = request.cookies.get('access_token')
	if not access_token:
		state = random_state()
		resp = make_response(render_template('./login.html', auth_url=authorization_url(secrets.CLIENT_ID, secrets.REDIRECT_URI, secrets.SCOPE, state)))
		resp.set_cookie('state', state)
		return resp
	else:
		resp = make_response(render_template('./form.html', test_repo=random.choice(repo_list)))
		return resp

@app.route('/', methods=['POST'])
def result():
	repo_url = request.form.get('repo')
	try:
		cleaned_repo = '/'.join(filter(lambda x: len(x) > 0, repo_url.split('/'))[-2:])
		access_token = request.cookies.get('access_token')
		r = api_request(access_token, repo_stat_endpoint(cleaned_repo))
		data = repo_stat(r.json())
		if data['cost'] < 1:
			return 'Please try again by refreshing this page.'
		else:
			data['cost'] = locale.currency(data['cost'], grouping=True )
			return make_response(render_template('./form.html', data=data, repo_url=repo_url, test_repo=random.choice(repo_list)))
	except Exception, e:
		print e
		return 'error'


@app.route('/auth_code', methods=['GET'])
def index():
	state = request.cookies.get('state')
	code = request.args.get('code')

	r = temp_code_to_access_code(secrets.CLIENT_ID, secrets.CLIENT_SECRET, code, secrets.REDIRECT_URI, state)
	try:
		j = r.json()
		access_token = j['access_token']
		resp = make_response(render_template('./form.html'))
		resp.set_cookie('access_token', access_token)
		return resp
	except Exception, e:
		print e
		print r.text
		return 'ERROR'


## Main

if __name__ == "__main__":
	app.debug = True
	app.run(host="0.0.0.0", port=5100)