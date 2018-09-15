from pymongo import MongoClient
HOSTNAME = "localhost"
USERNAME = "grader"
PASSWORD = "iamgrader011"
client = MongoClient(HOSTNAME, 27017)
client["admin"].authenticate(USERNAME, PASSWORD)
dbStaticAnalysis = client['staticAnalysis']
dbPrivacyGrading = client['privacygrading']
dbAndroidApp = client['androidApp']
