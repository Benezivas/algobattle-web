# Algorithmic Battle Web Framework

The lab course "Algorithmic Battle" is offered by the 
[Computer Science Theory group of RWTH Aachen University](https://tcs.rwth-aachen.de/)
since 2019. This repository contains the code to run a web server used to run the course

It can be used to distribute the necessary problem files, for students to upload their programs and reports, and to run
the battles themselves. This is done with a modern typescript frontend and fastAPI backend, with each process run in
an isolated docker environment.

# Usage
The only system requirement is a Docker installation. With it every part of the web server can be started with
`docker compose up`. The necessary configuration is specified with a `config.toml` file.

The primary code of the Algorithmic Battle course is hosted in [a different repository](https://github.com/Benezivas/algobattle)
that also contains further [documentation](www.algobattle.org/docs/).

# Funding
The development of this project was funded by
[`Stiftung Innovation in der Hochschullehre`](https://stiftung-hochschullehre.de/en/) (Project 
`FRFMM-106/2022 Algobattle`) and by the [Department of Computer Science of
RWTH Aachen University](https://www.informatik.rwth-aachen.de/go/id/mxz/?lidx=1).
