import pandas as pd
import os


os.system('mv media/data.csv deploy/text_classification/data.csv')

df = pd.read_csv("deploy/text_classification/data.csv")

intents = df['intent'].value_counts()
intents = intents.keys()

os.mkdir('deploy/text_classification/train')

os.chdir('deploy/text_classification/train')

for i in intents:
	os.mkdir(i)
for i in range(len(df)):
	with open(df['intent'][i]+'/'+str(i)+'.txt', 'w+', encoding='utf-8') as f:
		f.write(df['text'][i])
