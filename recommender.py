# -*- coding: utf-8 -*-
"""recommender.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1LaqPsLpzAkpdHCHY9Iv4Fd7YE07ct6VX
"""

from google.colab import drive
drive.mount('/content/drive')

import pandas as pd

anime_df = pd.read_csv('drive/MyDrive/anime_data/anime.csv')
ratings_df = pd.read_csv('drive/MyDrive/anime_data/rating_complete.csv')[:100000]
#lowered ratings dataframe length to free RAM

print(anime_df.shape)
print(ratings_df.shape)

anime_df.head()

ratings_df.head()

anime_names = anime_df.set_index('MAL_ID')['Name'].to_dict()

n_users = len(ratings_df.user_id.unique())
n_items = len(anime_df.MAL_ID.unique())

print(n_users)
print(n_items)

import torch
import numpy as np
from torch.autograd import Variable
from tqdm import tqdm_notebook as tqdm

class MatrixFactorization(torch.nn.Module):
  def __init__(self, n_users, n_items, n_factors = 20):
    super().__init__()
    self.user_factors = torch.nn.Embedding(n_users, n_factors)
    self.item_factors = torch.nn.Embedding(n_items, n_factors)
    self.user_factors.weight.data.uniform_(0, 0.05)
    self.item_factors.weight.data.uniform_(0, 0.05)

  def forward(self,data):
    #matrix algebra
    users, items = data[:,0], data[:,1]
    return self.user_factors(users)* self.item_factors((items)).sum(1)

  def predict(self, user, item):
    return self.forward(user, item)

from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader

class Loader(Dataset):
  def __init__(self):
    self.ratings = ratings_df.copy()

    users = ratings_df.user_id.unique()
    anime = ratings_df.anime_id.unique()

    self.userid2idx = {o: i for i, o in enumerate(users)}
    self.animeid2idx = {o: i for i, o in enumerate(anime)}

    self.idx2userid = {i: o for o, i in self.userid2idx.items()}
    self.idx2animeid = {i: o for o, i in self.animeid2idx.items()}

    self.ratings.animeId = ratings_df.anime_id.apply(lambda x: self.animeid2idx[x])
    self.ratings.userId = ratings_df.user_id.apply(lambda x: self.userid2idx[x])

    self.x = self.ratings.drop(['rating'], axis = 1).values
    self.y = self.ratings['rating'].values
    self.x, self.y = torch.tensor(self.x), torch.tensor(self.y)

  def __getitem__(self, index):
    return (self.x[index], self.y[index])

  def __len__(self):
    return len(self.ratings)

num_epochs = 32
cuda = torch.cuda.is_available()

print("Is running on GPU:", cuda)

model = MatrixFactorization(n_users, n_items, n_factors=4)
print(model)
for name, param in model.named_parameters():
    if param.requires_grad:
        print(name, param.data)
# GPU enable if you have a GPU...
if cuda:
    model = model.cuda()

# MSE loss
loss_fn = torch.nn.MSELoss()

# ADAM optimizier
optimizer = torch.optim.Adam(model.parameters(), lr=1e-2)

# Train data
train_set = Loader()
train_loader = DataLoader(train_set, 64, shuffle=True)

for it in tqdm(range(num_epochs)):
    losses = []
    for x, y in train_loader:
         if cuda:
            x, y = x.cuda(), y.cuda()
            optimizer.zero_grad()
            outputs = model(x)
            loss = loss_fn(outputs.squeeze(), y.type(torch.float32))
            losses.append(loss.item())
            loss.backward()
            optimizer.step()

# By training the model, we will have tuned latent factors for movies and users.
c = 0
uw = 0
iw = 0
for name, param in model.named_parameters():
    if param.requires_grad:
        print(name, param.data)
        if c == 0:
          uw = param.data
          c +=1
        else:
          iw = param.data
        #print('param_data', param_data)

trained_anime_embeddings = model.item_factors.weight.data.cpu().numpy()

len(trained_anime_embeddings)

from sklearn.cluster import KMeans
# Fit the clusters based on the movie weights
kmeans = KMeans(n_clusters=10, random_state=0).fit(trained_anime_embeddings)

for cluster in range(8):
  print("Cluster #{}".format(cluster))
  anims = []
  for anime_idx in np.where(kmeans.labels_ == cluster)[0]:
    anime_id = train_set.idx2animeid[anime_idx]
    rat_count = ratings_df.loc[ratings_df['anime_id']==anime_id].count()[0]
    anims.append((anime_names[anime_id], rat_count))
  for anim in sorted(anims, key=lambda tup: tup[1], reverse=True)[:10]:
    print("\t", anim[0])

