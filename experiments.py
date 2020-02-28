# # Graph of Docs
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.utils import shuffle
from sklearn.metrics import accuracy_score

from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier

from sklearn.svm import LinearSVC
from sklearn.linear_model import RidgeClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import chi2
from sklearn.feature_selection import SelectFromModel

from GraphOfDocs import utils
from GraphOfDocs import select
from GraphOfDocs.neo4j_wrapper import Neo4jDatabase

from collections import Counter

# Connect to database.
database = Neo4jDatabase('bolt://localhost:7687', 'neo4j', '123')

# Retrieve the communities of documents.
doc_communities = select.get_document_communities(database)
# Keep only the communities with more than one documents.
filtered_doc_communities = [doc_community for doc_community in doc_communities if doc_community[2] > 1]
# Fetch the selected documents.
selected_docs = sum([docs for _, docs, _ in filtered_doc_communities], [])
# Map community id to documents.
doc_communities_dict = {community_id: docs for community_id, docs, number_of_docs in filtered_doc_communities}
# Map document to community id.
doc_to_community_dict = {doc: community_id for community_id, doc_community, _ in filtered_doc_communities for doc in doc_community}

print(len(selected_docs))

# Read dataset, clean dataset and create a pandas dataframe of the dataset.
dataset = utils.read_dataset('/home/nkanak/Desktop/phd/experiments/GraphOfDocs/GraphOfDocs/data/20news-18828-all/')
# Create a label encoder (map classes to integer numbers).
le = LabelEncoder()
# The class of each document can be found by simply split (character '_') its filename. E.g. comp.sys.mac.hardware_51712.
le.fit([file[0].split('_')[0] for file in dataset])
# Tuple: file identifier, file class, file class number, file text.
clean_dataset = [(file[0], file[0].split('_')[0], le.transform([file[0].split('_')[0]])[0], ' '.join(utils.generate_words(file[1], extend_window=True, insert_stopwords=False, lemmatize=False, stem=False))) for file in dataset]
df = pd.DataFrame(clean_dataset, columns=['identifier', 'class', 'class_number', 'text'])
df_all = df

#df_not_selected = df[~df['identifier'].isin(selected_docs)]
# Keep only the selected documents (i.e. the document from the community with more than 1 documents).
df = df[df['identifier'].isin(selected_docs)]

#df_not_selected = shuffle(df_not_selected, random_state=42)
df = shuffle(df, random_state=42)
print(df.head(2))

# Number of unique classes
print('Number of unique classes: %s' % le.classes_.shape)

X = df['text']
y = df['class_number']

def benchmark_classifier(clf, X_train, y_train, X_test, y_test):
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print(accuracy_score(y_test, y_pred))
    return clf

# ## Running experiments with bag-of-words and widely-used classifiers.
positions = [i for i in range(len(X))]

cv = CountVectorizer()
# bag-of-words
X_transformed = cv.fit_transform(X)

X_train, X_test, y_train, y_test, positions_train, positions_test = train_test_split(X_transformed, y, positions, test_size=0.33, random_state=42)
print('Train size %s' % X_train.shape[0])
print('Test size %s' % X_test.shape[0])
print('Number of features %s' % X_test.shape[1])

bag_of_words_classifiers = [
    ('Naive Bayes', MultinomialNB()),
    ('Logistic Regression', LogisticRegression(random_state=0, solver='lbfgs', multi_class='multinomial')),
    ('5-NN', KNeighborsClassifier(n_neighbors=5, weights='distance')),
    ('2-NN', KNeighborsClassifier(n_neighbors=2, weights='distance')),
    ('1-NN', KNeighborsClassifier(n_neighbors=1, weights='distance')),
    ('Linear SVM', LinearSVC()),
    #('Neural Network 100x50', MLPClassifier(solver='adam', hidden_layer_sizes=(100, 50), random_state=42)),
    #('Neural Network 500x250', MLPClassifier(solver='adam', hidden_layer_sizes=(500, 250), random_state=42)),
    #('Neural Network 1000x500', MLPClassifier(solver='adam', hidden_layer_sizes=(1000, 500), random_state=42)),
]

for classifier in bag_of_words_classifiers:
    print(classifier[0])
    benchmark_classifier(classifier[1], X_train, y_train, X_test, y_test)

# ## Feature selection using classical methods

# ### Feature selection based on importance weights using a meta-transformer model
selector = SelectFromModel(estimator=LinearSVC()).fit(X_train, y_train)
X_selected_transformed = selector.transform(X_transformed)
X_selected_train, X_selected_test, y_selected_train, y_selected_test = train_test_split(X_selected_transformed, y, test_size=0.33, random_state=42)
print('Train size %s' % X_selected_train.shape[0])
print('Test size %s' % X_selected_test.shape[0])
print('Number of features %s' % X_selected_test.shape[1])

for classifier in bag_of_words_classifiers:
    print(classifier[0])
    benchmark_classifier(classifier[1], X_selected_train, y_selected_train, X_selected_test, y_selected_test)

# ### Performing feature selection by removing features with low variance.
variance_selector = VarianceThreshold(threshold=0.001).fit(X_train)
variance_X_transformed = variance_selector.transform(X_transformed)
X_selected_variance_train, X_selected_variance_test, y_selected_variance_train, y_selected_variance_test = train_test_split(variance_X_transformed, y, test_size=0.33, random_state=42)
print('Train size %s' % X_selected_variance_train.shape[0])
print('Test size %s' % X_selected_variance_test.shape[0])
print('Number of features %s' % X_selected_variance_test.shape[1])

for classifier in bag_of_words_classifiers:
    print(classifier[0])
    benchmark_classifier(classifier[1], X_selected_variance_train, y_selected_variance_train, X_selected_variance_test, y_selected_variance_test)

# ### Feature selection by selecting the best features based on univariate statistical tests (Kbest features)
kbest_selector = SelectKBest(chi2, k=20000).fit(X_train, y_train)
kbest_X_transformed = kbest_selector.transform(X_transformed)
X_kbest_train, X_kbest_test, y_kbest_train, y_kbest_test = train_test_split(kbest_X_transformed, y, test_size=0.33, random_state=42)
print('Train size %s' % X_kbest_train.shape[0])
print('Test size %s' % X_kbest_test.shape[0])
print('Number of features %s' % X_kbest_test.shape[1])

for classifier in bag_of_words_classifiers:
    print(classifier[0])
    benchmark_classifier(classifier[1], X_kbest_train, y_kbest_train, X_kbest_test, y_kbest_test)

# ### Bigrams generation using the comman way

# ## Running experiments with graph-of-docs.

# ### Graph-of-docs classifier
_, test_docs = train_test_split(df['identifier'], test_size=0.33, random_state=42)
test_docs = list(test_docs)
class_true = []
class_pred = []
for test_doc in test_docs:
    community_id = doc_to_community_dict[test_doc]
    community_docs = doc_communities_dict[community_id]
    classes = [doc.split('_')[0] for doc in community_docs if doc != test_doc]
    
    correct_class = test_doc.split('_')[0]
    classified_class = Counter(classes).most_common(1)[0][0]
    class_true.append(correct_class)
    class_pred.append(classified_class)
print('Accuracy: %s' % (accuracy_score(class_true, class_pred)))
# accuracy: 0.9752087682672234

# ## Feature selection using graph-of-docs

# ### Create a vocabulary with the TOP N words of each community of docs
train_docs = list(df.iloc[positions_train]['identifier'])
vocabulary = []
for doc in train_docs:
    for word in select.get_community_tags(database, doc_to_community_dict[doc], top_terms=250):
        vocabulary.append(word)
vocabulary = list(set(vocabulary))
cv = CountVectorizer(vocabulary=vocabulary)
# bag-of-words
X_transformed = cv.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_transformed, y, test_size=0.33, random_state=42)
print('Train size %s' % X_train.shape[0])
print('Test size %s' % X_test.shape[0])
print('Number of features %s' % X_test.shape[1])

for classifier in bag_of_words_classifiers:
    print(classifier[0])
    benchmark_classifier(classifier[1], X_train, y_train, X_test, y_test)

# ### [tag1, tag2, ... tagN] -> class (Do this for each community of docs)
train_docs = list(df.iloc[positions_train]['identifier'])
test_docs = list(df.iloc[positions_test]['identifier'])
all_docs = test_docs + train_docs
unique_community_ids = list(set([doc_to_community_dict[doc] for doc in train_docs]))

communities_y = []
communities_tags = []
for community_id in unique_community_ids:
    # Find the most common community class
    community_docs = doc_communities_dict[community_id]
    classes = [doc.split('_')[0] for doc in community_docs if doc not in test_docs]
    classified_class = Counter(classes).most_common(1)[0][0]
    communities_y.append(classified_class)
    # Get the most important tags of each community.
    communities_tags.append(' '.join(select.get_community_tags(database, community_id, top_terms=250)))

cv = CountVectorizer()
X_transformed = cv.fit_transform(communities_tags)

print('Number of features %s' % X_transformed.shape[1])
communities_y_encoded = le.transform(communities_y)

X_test_docs = []
for doc in list(df[df['identifier'].isin(test_docs)]['text']):
    X_test_docs.append(' '.join(list(set(doc.split()))))

X_test_docs_transformed = cv.transform(X_test_docs)
y_test = list(df[df['identifier'].isin(test_docs)]['class_number'])

print(X_transformed.shape)

for classifier in bag_of_words_classifiers:
    print(classifier[0])
    benchmark_classifier(classifier[1], X_transformed, communities_y_encoded, X_test_docs_transformed, y_test)

# ### Bigrams generation using graph-of-docs

database.close()
