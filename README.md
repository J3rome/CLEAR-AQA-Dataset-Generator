### CLEAR Dataset Generation
### Compositional Language and Elementary Acoustic Reasoning


We introduced the task of acoustic question answering (AQA) in https://arxiv.org/abs/1811.10561 <br>
We published a dataset for this task at https://ieee-dataport.org/open-access/clear-dataset-compositional-language-and-elementary-acoustic-reasoning

Here is the code that generate the CLEAR dataset.

#### Installation
This project was written in Python 3<br>
We recommend creating a virtual environment in order to keep clean dependencies<br>
Then, install the dependencies using the requirements.txt file
```
pip install -r requirements.txt
```

#### Overview of the generation process
<object data="./img/process_overview.pdf" type="application/pdf" width="700px" height="700px">
    <embed src="./img/process_overview.pdf">
        <p>This browser does not support PDFs. Please download the PDF to view it: <a href="https://www.dropbox.com/s/a1hdh6vlcoknwsb/software_achitecture.pdf?dl=0">Download PDF</a>.</p>
    </embed>
</object>
ADD POSTER GRAPH
1. Generation of the scenes definition
2. Generation of the questions based on the scenes definition
3. Production of the audio recordings of the scenes (Can also produce spectrograms)

To run the whole generation process with the default configuration simply run
``` 
./run_experiment.sh {VERSION_NB}
```

See **Default Arguments** section for a list of the default versions

#### Output
By default, a folder named `output` will be created at the root of this repository.
All generated files will be outputted in a sub-folder named `{VERSION_NB}`

```
- audio : Scene recordings (WAV format) separated by set
    - train
    - val
    - test
- questions : Question definitions (JSON format)
    - CLEAR_train_questions.json
    - CLEAR_val_questions.json
    - CLEAR_test_questions.json
- scenes : Scene definitions (JSON format)
    - CLEAR_train_scenes.json
    - CLEAR_val_scenes.json
    - CLEAR_test_scenes.json
- images : Scene spectrograms (PNG format) separated by set
    - train
    - val
    - test
- arguments : Copy of the arguments used at generation time (If run through run_generation.sh)
- logs : The whole generation process logs (If run through run_generation.sh)
```

#### Default Arguments
The folder `arguments` at the root of this repository contains the arguments list for each part of the generation process

They are divided by version (Simply create a new folder to add a new version):
```
    - v1.0.0_1k_scenes_20_inst_per_scene
    - v1.0.0_1k_scenes_40_inst_per_scene
    - v1.0.0_10k_scenes_20_inst_per_scene
    - v1.0.0_10k_scenes_40_inst_per_scene
    - v1.0.0_50k_scenes_20_inst_per_scene
    - v1.0.0_50k_scenes_40_inst_per_scene
```

See Scene Generation, Question Generation and Scene production for more infos on how their usage

#### Elementary Sounds
Each scenes is composed by assembling a serie of Elementary Sounds together.
The elementary sounds have been selected from the [Good-Sound Dataset](https://www.upf.edu/web/mtg/good-sounds)

In this first version of CLEAR, all elementary sounds are recordings of an instrument playing a single sustained note.

The elementary sounds bank can easily be upgraded by adding new sounds to the `elementary_sounds` folder and the `elementary_sounds.json` file.

This allow to create a whole new scenes with different sounds (Environmental, speech, etc).

#### Scene Generation
To run the scene generation process :
```
 python generate_scenes_definition.py @arguments/{VERSION_NB}/generate_scenes_definition.args --output_version_nb {VERSION_NB}
```


#### Question Generation
```
 python generate_questions.py @arguments/{VERSION_NB}/generate_{SET_TYPE}_questions.args --output_version_nb {VERSION_NB}
```

```
 python scripts/consolidate_questions.py --set_type {SET_TYPE} --output_version_nb {VERSION_NB}
```

#### Scene Production

```
 python produce_scenes_audio.py @arguments/{VERSION_NB}/produce_{SET_TYPE}_scenes_audio.args --output_version_nb {VERSION_NB}
```

The code published in this repository 

TODO :
* Logos (UdeS, KTH, IGLU, CHIST-ERA)
* Link to Paper & IEEE Dataport
* General description
* Requirements & Virtual Env
* Quick bullet points of the steps (Maybe poster graph ?)
* Produced files
* Elementary sounds
* Arguments folder
* Scene Generation
* Question Generation
    * Credit to CLEVR
* Scene Production
* Way to cite this research

# Environment setup
We suggest using a virtual environment to run this code
To make this directory discoverable by your python executable, create a Aqa-Dataset-Gen.pth file in the site-package directory of your virtual environment
It should contain the path to this folder. Ex :
```
~/dev/Aqa-Dataset-Gen
```




# CLEVR Dataset Generation

This is the code used to generate the [CLEVR dataset](http://cs.stanford.edu/people/jcjohns/clevr/) as described in the paper:

**[CLEVR: A Diagnostic Dataset for Compositional Language and Elementary Visual Reasoning](http://cs.stanford.edu/people/jcjohns/clevr/)**
 <br>
 <a href='http://cs.stanford.edu/people/jcjohns/'>Justin Johnson</a>,
 <a href='http://home.bharathh.info/'>Bharath Hariharan</a>,
 <a href='https://lvdmaaten.github.io/'>Laurens van der Maaten</a>,
 <a href='http://vision.stanford.edu/feifeili/'>Fei-Fei Li</a>,
 <a href='http://larryzitnick.org/'>Larry Zitnick</a>,
 <a href='http://www.rossgirshick.info/'>Ross Girshick</a>
 <br>
 Presented at [CVPR 2017](http://cvpr2017.thecvf.com/)

Code and pretrained models for the baselines used in the paper [can be found here](https://github.com/facebookresearch/clevr-iep).

You can use this code to render synthetic images and compositional questions for those images, like this:

<div align="center">
  <img src="images/example1080.png" width="800px">
</div>

**Q:** How many small spheres are there? <br>
**A:** 2

**Q:**  What number of cubes are small things or red metal objects? <br>
**A:**  2

**Q:** Does the metal sphere have the same color as the metal cylinder? <br>
**A:** Yes

**Q:** Are there more small cylinders than metal things? <br>
**A:** No

**Q:**  There is a cylinder that is on the right side of the large yellow object behind the blue ball; is there a shiny cube in front of it? <br>
**A:**  Yes

If you find this code useful in your research then please cite

```
@inproceedings{johnson2017clevr,
  title={CLEVR: A Diagnostic Dataset for Compositional Language and Elementary Visual Reasoning},
  author={Johnson, Justin and Hariharan, Bharath and van der Maaten, Laurens
          and Fei-Fei, Li and Zitnick, C Lawrence and Girshick, Ross},
  booktitle={CVPR},
  year={2017}
}
```

All code was developed and tested on Ubuntu 18.04 using Python 3.

## Step 1: Generating Images
First we render synthetic images using [Blender](https://www.blender.org/), outputting both rendered images as well as a JSON file containing ground-truth scene information for each image.

Blender ships with its own installation of Python which is used to execute scripts that interact with Blender; you'll need to add the `image_generation` directory to Python path of Blender's bundled Python. The easiest way to do this is by adding a `.pth` file to the `site-packages` directory of Blender's Python, like this:

```bash
echo $PWD/image_generation >> $BLENDER/$VERSION/python/lib/python3.5/site-packages/clevr.pth
```

where `$BLENDER` is the directory where Blender is installed and `$VERSION` is your Blender version; for example on OSX you might run:

```bash
echo $PWD/image_generation >> /Applications/blender/blender.app/Contents/Resources/2.78/python/lib/python3.5/site-packages/clevr.pth
```

You can then render some images like this:

```bash
cd image_generation
blender --background --python render_images.py -- --num_images 10
```

On OSX the `blender` binary is located inside the blender.app directory; for convenience you may want to
add the following alias to your `~/.bash_profile` file:

```bash
alias blender='/Applications/blender/blender.app/Contents/MacOS/blender'
```

If you have an NVIDIA GPU with CUDA installed then you can use the GPU to accelerate rendering like this:

```bash
blender --background --python render_images.py -- --num_images 10 --use_gpu 1
```

After this command terminates you should have ten freshly rendered images stored in `output/images` like these:

<div align="center">
  <img src="images/img1.png" width="260px">
  <img src="images/img2.png" width="260px">
  <img src="images/img3.png" width="260px">
  <br>
  <img src="images/img4.png" width="260px">
  <img src="images/img5.png" width="260px">
  <img src="images/img6.png" width="260px">
</div>

The file `output/CLEVR_scenes.json` will contain ground-truth scene information for all newly rendered images.

You can find [more details about image rendering here](image_generation/README.md).

## Step 2: Generating Questions
Next we generate questions, functional programs, and answers for the rendered images generated in the previous step.
This step takes as input the single JSON file containing all ground-truth scene information, and outputs a JSON file 
containing questions, answers, and functional programs for the questions in a single JSON file.

You can generate questions like this:

```bash
cd question_generation
python generate_questions.py
```

The file `output/CLEVR_questions.json` will then contain questions for the generated images.

You can [find more details about question generation here](question_generation/README.md).
