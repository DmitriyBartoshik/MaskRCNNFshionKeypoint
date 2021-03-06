# Author : Hellcat
# Time   : 2018/12/6

"""
import os
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
 
import numpy as np
np.set_printoptions(threshold=np.inf)
"""

import os
import numpy as np
import pandas as pd
from PIL import Image

import utils as utils
import model as modellib
from config import Config

import tensorflow as tf
import keras.backend.tensorflow_backend as KTF

config = tf.ConfigProto()
config.gpu_options.allow_growth = True
sess = tf.Session(config=config)
KTF.set_session(sess)

#PART_INDEX = {'blouse': [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14],
#              'outwear': [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
#              'dress': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 17, 18],
#              'skirt': [15, 16, 17, 18],
#              'trousers': [15, 16, 19, 20, 21, 22, 23]}

PART_INDEX = {'trousers': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}

PART_STR = ['waistband_left', 'waistband_center', 'waistband_right',
            'hip_left_out', 'knee_left_out', 'bottom_left_out',
            'bottom_left_in', 'knee_left_in',
            'crotch',
            'knee_right_in', 'bottom_right_in',
            'bottom_right_out', 'knee_right_out', 'hip_right_out']
# IMAGE_CATEGORY = ['blouse', 'outwear', 'dress', 'skirt', 'trousers'][2]
IMAGE_CATEGORY = ['trousers'][0]


class FIConfig(Config):
    """
    Configuration for training on the toy shapes dataset.
    Derives from the base Config class and overrides values specific
    to the toy shapes dataset.
    """
    # Give the configuration a recognizable name
    NAME = IMAGE_CATEGORY

    # Train on 1 GPU and 8 images per GPU. We can put multiple images on each
    # GPU because the images are small. Batch size is 8 (GPUs * images/GPU).
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1
    NUM_KEYPOINTS = len(PART_INDEX[IMAGE_CATEGORY])  # 更改当前训练关键点数目
    KEYPOINT_MASK_SHAPE = [56, 56]

    # Number of classes (including background)
    NUM_CLASSES = 1 + 1

    RPN_TRAIN_ANCHORS_PER_IMAGE = 100
    VALIDATION_STPES = 100
    STEPS_PER_EPOCH = 1000
    MINI_MASK_SHAPE = (56, 56)
    KEYPOINT_MASK_POOL_SIZE = 7

    # Pooled ROIs
    POOL_SIZE = 7
    MASK_POOL_SIZE = 14
    MASK_SHAPE = [28, 28]
    WEIGHT_LOSS = True
    KEYPOINT_THRESHOLD = 0.005


def image_size(path):
    with open(path, 'rb') as fp:
        im = Image.open(fp)
    w, h = im.size  # size函数返回的是w、h，也就是列、行
    return h, w


class FIDataset(utils.Dataset):
    """Generates the shapes synthetic dataset. The dataset consists of simple
    shapes (triangles, squares, circles) placed randomly on a blank surface.
    The images are generated on the fly. No file access required.
    """
    with_mask = False

    def load_FI(self, training=True):
        """Generate the requested number of synthetic images.
        count: number of images to generate.
        height, width: the size of the generated images.
        """
        csv_data = pd.concat([pd.read_csv('keypoint_data/train/Annotations/train.csv'),
                              pd.read_csv('keypoint_data/validation/Annotations/validation.csv')],
                             axis=0,
                             ignore_index=True  # 忽略索引表示不会直接拼接索引，会重新计算行数索引
                             )
        items_num = csv_data[csv_data.image_category.isin([IMAGE_CATEGORY])].shape[0]
        if training:
            load_data = csv_data[csv_data.image_category.isin([IMAGE_CATEGORY])][:int(items_num * 0.8)]
        else:
            load_data = csv_data[csv_data.image_category.isin([IMAGE_CATEGORY])][int(items_num * 0.8):]

        # Add classes
        self.add_class(source="FI", class_id=1, class_name=IMAGE_CATEGORY)

        # Add images
        for i in range(load_data.shape[0]):
            annotation = load_data.iloc[i]
            img_path = os.path.join("../keypoint_data", annotation.image_id)
            keypoints = np.array([p.split('_')
                                  for p in load_data.iloc[i][2:]], dtype=int)[PART_INDEX[IMAGE_CATEGORY], :]
            keypoints[:, -1] += 1
            if self.with_mask:
                w, h = image_size(img_path)
                self.add_image(source="FI",
                               image_id=i,
                               path=img_path,
                               width=w,
                               hight=h,
                               keypoints=keypoints)
            else:
                self.add_image(source="FI",
                               image_id=i,
                               path=img_path,
                               keypoints=keypoints)

    def load_keypoints(self, image_id):
        """
        Returns:
        key_points: num_keypoints coordinates and visibility (x,y,v)  [num_person,num_keypoints,3] of num_person
        masks: A bool array of shape [height, width, instance count] with
            one mask per instance.
        class_ids: a 1D array of class IDs of the instance masks, here is always equal to [num_person, 1]
        """
        keypoints = self.image_info[image_id]["keypoints"]
        class_ids = np.array([1])

        if self.with_mask:
            w, h = self.image_info[image_id]["width"], \
                   self.image_info[image_id]["hight"]
            mask = np.zeros([w, h], dtype=int)
            try:
                mask[keypoints[:, 1], keypoints[:, 0]] = 1
            except IndexError as e:
                print(e)
                print("Image serial number is {}".format(image_id))
                mask[keypoints[:, 1] - 1, keypoints[:, 0] - 1] = 1
            return np.expand_dims(keypoints, 0).copy(), np.expand_dims(mask, -1), class_ids
        return np.expand_dims(keypoints, 0).copy(), None, class_ids


if __name__ == "__main__":
    config = FIConfig()

    # import visualize
    # from model import log
    #
    # dataset = FIDataset()
    # dataset.load_FI()
    # dataset.prepare()
    # image_num = np.random.randint(0, 10000)
    # original_image, image_meta, gt_class_id, gt_bbox, gt_keypoint =\
    #     modellib.load_image_gt_keypoints(dataset, FIConfig, 624)
    # log("original_image", original_image)
    # log("image_meta", image_meta)
    # log("gt_class_id", gt_class_id)
    # log("gt_bbox", gt_bbox)
    # log("gt_keypoint", gt_keypoint)
    # visualize.display_keypoints(original_image,gt_bbox,gt_keypoint,gt_class_id,dataset.class_names)

    data_tra = FIDataset()
    data_tra.load_FI()
    data_tra.prepare()

    data_val = FIDataset()
    data_val.load_FI(training=False)
    data_val.prepare()

    model_dir = './logs_{}'.format(IMAGE_CATEGORY)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    model = modellib.MaskRCNN(mode='training',
                              config=config,
                              model_dir=model_dir)

    try:
        model.load_weights(model.find_last()[1], by_name=True,
                           exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",
                                    "mrcnn_bbox", "mrcnn_mask"])
    except TypeError as e:
        model.load_weights('./mask_rcnn_coco.h5', by_name=True,
                           exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",
                                    "mrcnn_bbox", "mrcnn_mask"])

    model.train(data_tra, data_val,
                learning_rate=config.LEARNING_RATE / 10,
                epochs=400, layers='heads')
