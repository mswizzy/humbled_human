import pymongo
import datetime
import os
from dotenv import load_dotenv

## necessary for python-dotenv ##
#APP_ROOT = os.path.join(os.path.dirname(__file__), '..')   # refers to application_top
BASEDIR = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(BASEDIR, '.env')
#dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)


mongo = os.getenv('MONGO')
client=pymongo.MongoClient(mongo)

#client = pymongo.MongoClient(os.getenv('MONGO'))

#create new database
db = client['humbled']
print('database created')
print(client.list_database_names())
#create tables
users = db['users']
roles = db['roles']
posts = db['posts']
causes = db['causes']

print(list(db.collection.find({})))



def add_role(role_name):
    role_data = {
        'role_name': role_name
    }
    return roles.insert_one(role_data)



def add_user(username,first_name, last_name, email, password, organization, dob, role):
    user_data = {
        'username': username,
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'password': password,
        'organization' : organization,
        'dob': dob,
        'join_date': datetime.datetime.now(),
        'role': role
    }
    return users.insert_one(user_data)
    

def add_cause(cause_name):
    cause_data = {
        'cause': cause_name
    }
    return causes.insert_one(cause_data)

def add_post(title, organization, cause, link, description, username):
    post_data = {
        'title': title,
        'organization': organization,
        'cause': cause,
        'link': link, 
        'description': description,
        'username': username,
        'date_added': datetime.datetime.now(),
        'date_modified': datetime.datetime.now()
    }
    return posts.insert_one(post_data)


def initial_database():
    # add roles
    admin = add_role('admin')
    contributor = add_role('contributor')
    user = add_role('user')
    
    # add users
    maria = add_user('swizzy', 'M', 'H', 'hall@maria.com', 'abc123', 'dogmom', '01/08/1998', 'admin')
    #add_user('mswizz', 'Maria', 'Hall', 'maria@h.com', 'brewer123', 'dog moms united', '01/08/1998', 'admin')
    
    # add categories
    lgbtq = add_cause('LQBTQ')
    blm = add_cause('Black Lives Matter')
    womens_rights = add_cause("Women's Rights")
    health = add_cause('Health')
    environment = add_cause('Environment')
    other = add_cause('Other')
    
   
    # add recipe
    test_post = add_post('Wooh, a test!', 'Super Seniorville', 'LGBTQ', 'www.uiowa.edu','Ta-da! Here it is...the official test post of Humbled Human. Iconic.', 'mswizzy')
    

def main():
    initial_database()
   

main()
