How to get started
==================

System level you should have pipenv installed. It is probably packaged, you can check on their webpage for steps. If
you are not using it for your projects, you should. It is a mix between virtualenv and pip (it uses both below) and
basically manages everything.

So, once you have installed, place yourself in this folder in the command line and run:

* If you just want to run the bot: `pipenv install`

* If you want to develop: `pipenv install -d`

If these steps don't work, report it so that I can update this with relevant steps.

After installing dependencies, we are ready to install this as a package. The command is `python setup.py develop`. I
you can also do `python setup.py install` but it's better to keep the installation linked to this directory instead of
having setuptools package and install the bot separately. If you have doubts on what I just said,
https://stackoverflow.com/questions/19048732/python-setup-py-develop-vs-install

Just in case, as an editor, I recommend pycharm, it's free (community edition) and it is light years ahead of the rest
of alternatives, you are free to do whatever you want.

Now you should be able to run the bot... Nope, not yet.

Apart from the bot code, you also need a database to link it to. You can link it to whatever postgres db you want, but
I would recommend you to run a local instance.

If you have Docker and docker-compose installed, this is a really good way to run packaged software. There are complete
guides on the internet, on how to run them, but for the basics:

* Install Docker using your package manager or as suggested in their webpage

* Install docker-compose, same thing, or package manager or as in the webpage (it's just an script), btw, it's in
  python, so you can also install it with pip, but I would discourage this

* Open a terminal in this folder, this terminal will be used all the time while your bot is up to maintain up the
  database. There are other ways to run it in the background, but I don't like them.

* In the terminal in this folder, run `docker-compose up`. This will download and run the packaged software (the
  postgres database in this case).

* We now have to give structure to the database, run `alembic upgrade head` to setup all the tables etc. there.

* Now, in the other terminal, you can finally launch the bot command running `bot`.

The output of that command should be self explainatory. Now, you can go to the different files to read what each one
contains. But I will outline here the structure a little:

* The more inner layer and the thing that most defines the bot is the Data Model. This are the Entities that we
  manage, and they are in `mosbot/db.py`.

* From there, because we have no ORM at the moment (asyncio doesn't have an async ORM yet), we have all the functions
  and queries that operate on the data in `mosbot/query.py`.

* Now you should be able to gather/write data and make some operations. There are some operations that are not as
  "simple" as the queries, and these are the "usecases" where you have a whole flow of queries and data transformation.
  The place where these are stored is in `mosbot/usecase.py`

* Finally, in the most outer layer, you have the two main "interfaces", this is where we receive the data from the
  `abot` library and we have the handlers and commands. The files are, `mosbot/handler.py` for event handlers and
  `mosbot/command.py` for the commands.

* There are two other files, that are "transversal" that are the `mosbot/utils.py` and `mosbot/config.py`.


You should think of this architecture (file structure/function dependencies) as an onion. The idea is that the most
inner part (db) only knows about itself. The second layer would know about db and itself, and so on and so forth. If
you are curious, it's called clean architecture, and I have adopted it for python from some talks I saw for Android.

Check out the files and please do send pull requests.


Contributions
-------------

Contributions are going to be reviewed, and I will propose changes. I may end up changing the whole structure of the
code, but that doesn't mean you did bad code or anything, it's just that toward the ampliations plans of the bot, it
makes sense to have this structure.

Tests are really welcome, and because this is already in production, complete failure proof and not affecting ongoing
operations is expected.
