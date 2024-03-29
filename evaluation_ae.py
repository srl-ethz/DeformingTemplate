import torch
import argparse
import numpy as np
from foldingNet_model import AutoEncoder
#from chamfer_distance.chamfer_distance import ChamferDistance
from dataset import PointClouds
from modelAya import Autoencoder

import torch.nn as nn
import torch.nn.functional as F
import torch.nn.init as init


import trimesh 
import os
import open3d as o3d
from pytorch3d.loss import (
    chamfer_distance, 
    mesh_edge_loss, 
    mesh_laplacian_smoothing, 
    mesh_normal_consistency,
)
parser = argparse.ArgumentParser()
parser.add_argument('--encoder_type', type=str, default='2018')
args = parser.parse_args()

config='3'
#Mean Chamfer Distance of all Point Clouds: tensor(0.0010)
if(config == "0"):
    folder='/home/elham/srl-nas/elham/research_project/logs/auto2018_256dim_3000points_NoAug_1seq_5ycb/'
    args.k=256
    val_folder='/home/elham/srl-nas/elham/watertight/ycb/ycb_mult_5_one_seq/val'
#Mean Chamfer Distance of all Point Clouds: tensor(0.0010) scissor tensor(0.0007)
elif(config == "1"):
    folder='/home/elham/srl-nas/elham/research_project/logs/auto2018_1024dim_3000points_NoAug_1seq_5ycb/'
    args.k=1024
    val_folder='/home/elham/srl-nas/elham/watertight/ycb/ycb_mult_5_one_seq/val'
#Mean Chamfer Distance of all Point Clouds: tensor(0.0011)
elif(config == "2"):
    folder='/home/elham/srl-nas/elham/research_project/logs/first_50_each_folding_3000_256dim'
    args.k=256
    val_folder='/home/elham/srl-nas/elham/watertight/ycb/ycb_mult_5_one_seq/val'
#Mean Chamfer Distance of all Point Clouds: tensor(0.0011)
elif(config == "3"):
    folder='/home/elham/srl-nas/elham/research_project/logs/first_50_each_folding_3000_1024dim'
    args.k=1024
    val_folder='/home/elham/srl-nas/elham/watertight/ycb/ycb_mult_5_one_seq/val'
#Mean Chamfer Distance of all Point Clouds: tensor(0.0002)
elif(config == "4"):
    folder='/home/elham/srl-nas/elham/research_project/logs/auto2018_1024dim_3000points_NoAug_1000seq_scissor'
    args.k=1024
    val_folder='/home/elham/srl-nas/elham/watertight/ycb/ycb_mult_1_thousand_seq/val'
#Mean Chamfer Distance of all Point Clouds: tensor(0.0002)
elif(config == "5"):
    folder='/home/elham/srl-nas/elham/research_project/logs/auto2018_1024dim_3000points_NoAug_1seq_scissor'
    args.k=1024
    val_folder='/home/elham/srl-nas/elham/watertight/ycb/ycb_mult_5_one_seq/val_sc'
#Mean Chamfer Distance of all Point Clouds: tensor(0.0010) just sc: (0.0003)
elif(config == "6"):
    folder='/home/elham/srl-nas/elham/research_project/logs/auto2018_1024dim_3000points_NoAug_1000seq_5ycb'
    args.k=1024
    #val_folder='/home/elham/Desktop/makeDataset/warping/warping_shapes_generation/build_path/ycb_mult_1_thousand_seq/val'
    val_folder='/home/elham/hdd/data/ycb/ycb_mult_5_thousand_seq/val'
    justSc = False
    if(justSc):
        val_folder='/home/elham/srl-nas/elham/watertight/ycb/ycb_mult_5_one_seq/val_sc'

numOfPoints =  3000
test_dataset = PointClouds(val_folder, is_training=True, num_points=numOfPoints)

if(config == "0" or config == "1" or config == "4" or config == "5" or config == "6"):
    args.encoder_type = "2018"
else:
    args.encoder_type = "folding"

device='cuda:0'
test_dataloader = torch.utils.data.DataLoader(test_dataset, batch_size=4, shuffle=False, num_workers=4)
if(args.encoder_type == '2018'):
    def weights_init(m):
        if isinstance(m, nn.Conv1d):
            init.kaiming_uniform_(m.weight)
            if m.bias is not None:
                init.zeros_(m.bias)
        elif isinstance(m, nn.BatchNorm1d):
            init.ones_(m.weight)
            init.zeros_(m.bias)

    autoencoder = Autoencoder(k=args.k, num_points=numOfPoints).to(device)
    autoencoder = autoencoder.apply(weights_init).to(device)
elif(args.encoder_type == 'folding'):
    autoencoder = AutoEncoder(k=args.k)

#folder='/home/elham/Desktop/deformTemplate/first_50_each_2018_256dim'

os.makedirs(folder+'/plies/', exist_ok=True)
if(args.encoder_type == '2018'):
    dict = torch.load(folder+'/models/check_min.pt', map_location='cuda:0')
    autoencoder.load_state_dict(dict["model"])
else:
    if(os.path.exists(folder+'/logs/model_lowest_cd_loss.pth')):
        file = folder+'/logs/model_lowest_cd_loss.pth'
    else:
        file = folder+'/logs/model_epoch_9000.pth'
    dict = torch.load(file, map_location='cuda:0')
    autoencoder.load_state_dict(dict["model_state_dict"])


#autoencoder.load_state_dict(dict["model_state_dict"])
#autoencoder.load_state_dict(dict["model"])
device = torch.device('cuda')
autoencoder.to(device)

#cd_loss = ChamferDistance()

# evaluation
autoencoder.eval()
total_cd_loss = 0

losses = []
lossIndividus = {}
keys = {'scissor', 'bleach', 'hammer', 'orange', 'brick', 'dice'}
for key in keys:
    lossIndividus[key]=[]
with torch.no_grad():
    print('length of the test dataset: ', len(test_dataset))
    allLosses=[]
    id = 0
    for data, p, mean, scale in test_dataloader:
        #print('data.shape: ', data.shape)
        print('p: ', p)
        #if(id > 1):
        #    break
        point_clouds = data
        b, _, _ = point_clouds.shape
        point_clouds = point_clouds#.permute(0, 2, 1)
        point_clouds = point_clouds.to(device)
        print('pointclouds shape: ', point_clouds.shape)
        _, recons = autoencoder(point_clouds)
        #print('recons shape: ', recons[0,...].permute(1,0).shape)
        os.environ['PYOPENGL_PLATFORM'] = 'egl'
        #color = np.ones_like(recons[0,...].permute(1,0).cpu().numpy())
        #cloud = trimesh.PointCloud(vertices=recons[0,...].permute(1,0).cpu().numpy(), colors=color)
        #cloud.show(background=[0,0,0,0])
        pcd = o3d.geometry.PointCloud()
        #print('x shape: ', x.shape)
        for i in range(b):
            x_restored_ = (recons[i,...].permute(1,0) * scale[i].to('cuda')+ mean[i].to('cuda'))
            print('x_restored_ shape: ', x_restored_.shape)
            pcd.points = o3d.utility.Vector3dVector(np.float32(x_restored_.cpu().numpy()))#.float32)
            print('folder name: ', folder+'/plies/decoded_'+p[i]+'.ply')
            o3d.io.write_point_cloud(folder+'/plies/decoded_'+p[i]+'.ply', pcd)
            print('point_clouds shape: ', point_clouds.shape)
            ls = chamfer_distance(point_clouds[i].unsqueeze(0).permute(0, 2, 1), recons[i].unsqueeze(0).permute(0, 2, 1))
            allLosses.append(ls[0].cpu())
            print(ls[0].cpu())
            #total_cd_loss += ls[0].cpu()

            for key in keys:
                if(key in p[i]):
                    ls = chamfer_distance(point_clouds.permute(0, 2, 1), recons.permute(0, 2, 1))
                    #print(key, ' ', lossIndividus)
                    lossIndividus[key].append(ls[0].cpu())
        id+=1
    #np.savetxt('errors_04379243.txt', allLosses, delimiter=',') 
for key in keys:
    if(len(lossIndividus[key])==0):
        print('does not exist')
    else:    
        print('loss for key: ', key, sum(lossIndividus[key])/len(lossIndividus[key]))

# calculate the mean cd loss
#mean_cd_loss = total_cd_loss / len(test_dataset)
loss_mean = sum(allLosses) / len(allLosses)
print('loss Chamfer Distance for all Point Clouds: ', loss_mean)
#print('Mean Chamfer Distance of all Point Clouds:', mean_cd_loss)
