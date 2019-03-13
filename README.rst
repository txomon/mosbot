
How to get started
------------------

1.  Install *Pipenv* at a system level

    If you are not using it for your projects, you should. *Pipenv* is a mix between *pip* and *virtualenv* (it uses
    both of them below) and basically manages everything. You can probably find *Pipenv* packaged, check their webpage
    for installation steps.

2.  Install dependencies

    In a command line, navigate to the current project directory and install the dependencies by running one of the
    commands below.

    * To use the bot: ``pipenv install``

    * To develop: ``pipenv install -d``

    If these steps don't work, please report it so that I can update these instructions with relevant steps.

3.  Install *mostbot* as a package

    Run the command ``python setup.py develop``. You can also do ``python setup.py install``, but it's better to keep the
    installation linked to this directory instead of having ``setuptools`` package and install the bot separately. If you
    have doubts on what I just said, https://stackoverflow.com/questions/19048732/python-setup-py-develop-vs-install

4.  Install a database

    Apart from the bot code, you also need a database to link the bot to. You can link it to whatever *PostgreSQL*
    database you want, but I would recommend you to run a local instance.

    Using *Docker* and *Docker Compose* is a really good way to run packaged software. There are complete guides on the
    internet about how to run them, but for the basics:

    1.  Install *Docker* either using your package manager or as suggested in *Docker*'s official webpage. By the way,
        the official website method is just a Python script, so you can also install it with *pip* (I would
        discourage this option).

    2.  Install *Docker Compose*. Same thing as *Docker*: user either package manager or the official webpage script.

    3.  Open another terminal in this folder. This new terminal will be used all the time to maintain up the database
        while your bot is running. There are other ways to run the database in the background, but I recommend this
        one.

    4.  In the new terminal, run ``docker-compose up`` to download and run the packaged software (the *PostgreSQL*
        database in this case).

    5.  Run ``alembic upgrade head`` to create the database structure by setting up all the database tables, etc.

5.  Launch *mosbot*

    Go back to the first terminal, and run ``bot`` to launch. The output of the command should be self explanatory.



Project structure
-----------------

This is a brief outline to cover the basics of the project structure:

*   The more inner layer and the thing that most defines the bot is the Data Model. This are the Entities that we
    manage, and they are in ``mosbot/db.py``.

*   From there, because we have no ORM at the moment (asyncio doesn't have an async ORM yet), we have all the functions
    and queries that operate on the data in ``mosbot/query.py``.

*   Now you should be able to gather/write data and make some operations. There are some operations that are not as
    "simple" as the queries, and these are the "usecases" where you have a whole flow of queries and data transformation.
    The place where these are stored is in ``mosbot/usecase.py``

*   Finally, in the most outer layer, you have the two main "interfaces", this is where we receive the data from the
    ``abot`` library and we have the handlers and commands. The files are, ``mosbot/handler.py`` for event handlers and
    ``mosbot/command.py`` for the commands.

*   There are two other files, that are "transversal" that are the ``mosbot/utils.py`` and ``mosbot/config.py``.


You should think of this architecture (file structure/function dependencies) as an onion. The idea is that the most
inner part (the database) only knows about itself. The second layer would know about the database and itself, and so on
and so forth. If you are curious, it's called *Clean Architecture*, and I have adopted it for Python from some talks
I saw for Android.

Check out the files and please do send pull requests.



Further recommendations
-----------------------

*   **Editor**: I personally recommend *PyCharm*. Its *Community Edition* is free and it is light years ahead of the
    rest of alternatives. Of course, you are free to choose whichever editor you want.


Using the Helm chart
--------------------

1.  Fetch/update chart dependencies:

    .. code-block:: bash

       helm dependency update ./helm


2.  Install mosbot chart:

    .. code-block:: bash

       helm install ./helm


Contributions
-------------

Contributions are going to be reviewed, and I will propose changes. I may end up modifying the whole structure of the
code, but this modification doesn't mean you did bad code or similar. It's just that it makes sense to have a certain
structure for the bot to grow.

Tests are really welcome, and because this project is already in production, complete failure proof and not affecting
ongoing operations is expected.