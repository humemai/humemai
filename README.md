# humemai

[![DOI](https://zenodo.org/badge/614376180.svg)](https://zenodo.org/doi/10.5281/zenodo.10876440)
[![PyPI
version](https://badge.fury.io/py/humemai.svg)](https://badge.fury.io/py/humemai)

This repo hosts a package `humemai`, a human-like memory systems that are modeled with
knowledge knoweldge graphs (KGs). At the moment they are nothing but a Python list of
RDF quadruples, but soon it'll be a better object type so that they can be compatible
with graph databases, e.g., RDFLib, GraphDB, Neo4j, etc. Making it compatible with
RDFLib is top priority and it'll come with v2. There have been both [academic
papers](#list-of-academic-papers-that-use-humemai) and
[applications](#list-of-applications-that-use-humemai) that have used this package.

## Installation

```shell
pip install humemai
```

python>=3.8

## List of academic papers that use HumemAI

- ["A Machine With Human-Like Memory Systems"](https://arxiv.org/abs/2204.01611)
- ["A Machine with Short-Term, Episodic, and Semantic Memory
  Systems"](https://arxiv.org/abs/2212.02098)
- ["Leveraging Knowledge Graph-Based Human-Like Memory Systems to Solve Partially Observable Markov Decision Processes"](https://arxiv.org/abs/2408.05861)

## List of applications that use HumemAI

## pdoc documentation

Click on [this link](https://humemai.github.io/humemai) to see the HTML rendered
docstrings

## Contributing

Contributions are what make the open source community such an amazing place to be learn,
inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
1. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
1. Run `make test && make style && make quality` in the root repo directory, to ensure
   code quality.
1. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
1. Push to the Branch (`git push origin feature/AmazingFeature`)
1. Open a Pull Request

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Authors

- [Taewoon Kim](https://taewoon.kim/)
