---
title: python-faker-duckdb-exploration
content_type: blog
source_url: https://motherduck.com/blog/python-faker-duckdb-exploration
indexed_at: '2025-11-25T19:58:16.040708'
content_hash: 9b4a4fd598022ca3
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Python Faker for DuckDB Fake Data Generation

2023/01/31 - 9 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

## Why generate data?

There is a plethora of interesting public data out there. The DuckDB community regularly uses the [NYC Taxi Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) to demonstrate and test features as it’s a reasonably large set of data (billions of records) and it’s data the public understands. We’re very lucky to have this dataset, but like many data sources, the data is in need of cleaning.

You can see here that some taxi trips were taken seriously far in the future. Based on the `fare_amount` for the following 5 person trip in 2098, I’d say we can safely conclude that inflation will be on a downward or lateral trend over the next 60 years.

```plaintext
Copy code

┌──────────────────────┬──────────┬─────────────────┬─────────────┐
│ tpep_pickup_datetime │ VendorID │ passenger_count │ fare_amount │
│      timestamp       │  int64   │      int64      │   double    │
├──────────────────────┼──────────┼─────────────────┼─────────────┤
│ 2098-09-11 02:23:31  │        2 │               5 │        22.5 │
│ 2090-12-31 06:41:26  │        2 │               2 │        52.0 │
│ 2088-01-24 00:25:39  │        2 │               1 │        14.5 │
│ 2088-01-24 00:15:42  │        2 │               1 │         4.5 │
│ 2084-11-04 12:32:24  │        2 │               1 │        10.0 │
```

Interestingly all trips with dates in the future are posted from a single vendor (see [data dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf)). [Others have documented](https://www.r-bloggers.com/2016/01/data-cleaning-part-1-nyc-taxi-trip-data-looking-for-stories-behind-errors/) additional issues with dirty data. Of course, I could clean these up, but using these records as-is makes me frequently question my SQL skills. I’d rather use generated data where analysts can focus on how ducking awesome DuckDB is instead of how unclean the data is.

As a bonus, using generated data allows us to create data that’s better aligned with real-world uses cases for the average analyst, as Anna Geller requests in a [recent tweet](https://twitter.com/anna__geller/status/1619134809959448578).

Twitter Embed

[Visit this post on X](https://twitter.com/anna__geller/status/1619134809959448578?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F) [Visit this post on X](https://twitter.com/thetinot/status/1619075080457428992?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

[![](https://pbs.twimg.com/profile_images/1586114576558718976/Pdb0o522_normal.jpg)](https://twitter.com/thetinot?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

[Tino Tereshko ![🇺🇦](https://abs-0.twimg.com/emoji/v2/svg/1f1fa-1f1e6.svg)](https://twitter.com/thetinot?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

·

[Jan 27, 2023](https://twitter.com/thetinot/status/1619075080457428992?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

[@thetinot](https://twitter.com/thetinot?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

·

[Follow](https://twitter.com/intent/follow?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F&screen_name=thetinot)

[View on X](https://twitter.com/thetinot/status/1619075080457428992?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

Twittersphere, what public datasets should we preload into [@motherduck](https://twitter.com/motherduck?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es2_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F) ??

[![](https://pbs.twimg.com/profile_images/1805968669228310528/cCC6Fy3M_normal.jpg)](https://twitter.com/anna__geller?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

[Anna Geller](https://twitter.com/anna__geller?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

[@anna\_\_geller](https://twitter.com/anna__geller?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

·

[Follow](https://twitter.com/intent/follow?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F&screen_name=anna__geller)

As a user, I would appreciate some randomly generated datasets where folks can analyze real world things like costs and revenue rather than petal lengths

[12:46 AM · Jan 28, 2023](https://twitter.com/anna__geller/status/1619134809959448578?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

[X Ads info and privacy](https://help.twitter.com/en/twitter-for-websites-ads-info-and-privacy)

[11](https://twitter.com/intent/like?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F&tweet_id=1619134809959448578) [Reply](https://twitter.com/intent/tweet?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F&in_reply_to=1619134809959448578)

Copy link

[Read 2 replies](https://twitter.com/anna__geller/status/1619134809959448578?ref_src=twsrc%5Etfw%7Ctwcamp%5Etweetembed%7Ctwterm%5E1619134809959448578%7Ctwgr%5E54342deb1e9be963d39036166eba90f1d16da307%7Ctwcon%5Es1_&ref_url=https%3A%2F%2Fmotherduck.com%2Fblog%2Fpython-faker-duckdb-exploration%2F)

> As a user, I would appreciate some randomly generated datasets where folks can analyze real world things like costs and revenue rather than petal lengths
>
> — Anna Geller (@anna\_\_geller) [January 28, 2023](https://twitter.com/anna__geller/status/1619134809959448578?ref_src=twsrc%5Etfw)

## Using Python Faker

[Faker](https://faker.readthedocs.io/en/master/) is a Python package for generating fake data, with a large number of providers for generating different types of data, such as people, credit cards, dates/times, cars, phone numbers, etc. Many of the [included](https://faker.readthedocs.io/en/master/providers.html) and [community](https://faker.readthedocs.io/en/master/providers.html) providers are even [localized](https://faker.readthedocs.io/en/master/locales.html) for different regions \[where bank accounts, phone numbers, etc are different\].

Keep in mind that the data we generate won’t be perfect \[distributions, values, etc\] unless we tune the out-of-the-box code. But oftentimes you just need someone who looks quacks like a dock, but is not an actual duck.

![python_faker_duck.jpg](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpython_faker_duck_9f1c0849b5.jpg&w=3840&q=75)

Here’s a simple example of using Python Faker to generate a person record, with a name, email, company, etc.:

```python
Copy code

import random
from faker import Faker

fake = Faker()

person = {}
# person['id'] = fake.ssn()
person['id'] = random.randrange(1000,9999999999999)
person['first_name'] = fake.first_name()
person['last_name'] = fake.last_name()
person['email'] = fake.unique.ascii_email()
person['company'] = fake.company()
person['phone'] = fake.phone_number()
```

You’ll notice I commented out generating the ID as a US Social Security Number (SSN), because that’s just scary and bad practice. Instead, I generated a random number in a specified range using [random](https://docs.python.org/3/library/random.html). This value is not guaranteed to be unique, so you might want to check for uniqueness in your python code. Alternatively, you could add a UNIQUE or PRIMARY KEY constraint in DuckDB (here are the [internals and examples](https://duckdb.org/2022/07/27/art-storage.html)), but that could generate too much work during loading large amounts of data.

Additional caveat: there is no guarantee of consistency between company name, email, and the first/last name – you could easily end up with:

```plaintext
Copy code

{'id': 7529464536979,
 'first_name': 'Vanessa',
  'last_name': 'Snyder',
  'email': 'margaret91@yahoo.com',
  'company': 'Garcia, James and Fisher',
  'phone': '902-906-4495x0016'}
```

## Inserting Data into DuckDB

There are at least four different ways to insert this generated data into DuckDB:

- SQL prepared statements
- Pandas DataFrames inserted directly into DuckDB
- CSV files copied into DuckDB
- Parquet files copied into DuckDB

As it’s the least efficient way and not recommended, I’m not going to demonstrate how to use prepared statements with `executemany`. The DuckDB documentation [explicitly warns against](https://duckdb.org/docs/api/python/overview.html) this method.

### Pandas DataFrames directly into DuckDB

DuckDB in Python has access to Pandas DataFrame objects in the current scope. In order to insert the `person` dict into a DuckDB database, you can create a DataFrame from the dict and execute a DuckDB SQL query like `CREATE TABLE persons AS SELECT * from df`.

Here’s an example of inserting 10 generated persons into a table of the same name in DuckDB:

```python
Copy code

​​import random
import duckdb
import pandas as pd
from faker import Faker
import fastparquet
import sys

fake = Faker()

def get_person():
  person = {}
  person['id'] = random.randrange(1000,9999999999999)
  person['first_name'] = fake.first_name()
  person['last_name'] = fake.last_name()
  person['email'] = fake.unique.ascii_email()
  person['company'] = fake.company()
  person['phone'] = fake.phone_number()
  return person

personlist = []
for x in range(10):
  personlist.append(get_person())

df = pd.DataFrame.from_dict(personlist)

con = duckdb.connect()
con.execute("CREATE TABLE persons AS SELECT * FROM df")
```

### CSV files copied into DuckDB

If you’ve worked with CSV files in Python, you’re probably already familiar with the csv module and perhaps the CSV [DictWriter](https://docs.python.org/3/library/csv.html#csv.DictWriter) constructor.

Once we have a `person` it’s quite easy to write that person to a CSV file. You’ll notice that I append the the first command-line argument as a suffix on the filename. You’ll understand the reason for this when we go to parallelize the execution of this code later in the post.

```python
Copy code

pcsv = open('out/persons_%s.csv' % sys.argv[1], 'w')

pwriter = csv.DictWriter(pcsv, fieldnames=['id','first_name','last_name','email','company','phone'])

pwriter.writeheader()
pwriter.writerow(person)
```

### Parquet files copied into DuckDB

Pandas DataFrames are actually a great way to create parquet files which can then be loaded into DuckDB. After we create a DataFrame containing 10 person records (in the code above), we can use the [fastparquet](https://pypi.org/project/fastparquet/) library to write them to a parquet file:

```python
Copy code

# Write out pandas DataFrame df to parquet, using suffix passed on command-line
fastparquet.write('outfile_%s.parquet' % sys.argv[1], df)
```

Instead of only generating 10 records at a time, I changed the code to generate 100k person records and save them into a parquet file:

```python
Copy code

personlist = []
for x in range(10):
  personlist.append(get_person())

df = pd.DataFrame.from_dict(personlist)
fastparquet.write('outfile_%s.parquet' % sys.argv[1], df)
```

This only took 26 seconds to execute:

```plaintext
Copy code

# time the execution of my python code
# use 6 as the suffix for the parquet file as i already have outfile_[1-5]
time python generate.py 6
python generate.py 6  28.35s user 0.22s system 108% cpu 26.241 total
```

Of course, we probably want to check that this worked well and that’s super easy to do using DuckDB to read the parquet files, using simple glob patterns:

```plaintext
Copy code

$ echo "SELECT id,first_name,last_name FROM 'outfile_*.parquet'" | duckdb
┌───────────────┬─────────────┬───────────┐
│      id       │ first_name  │ last_name │
│     int64     │   varchar   │  varchar  │
├───────────────┼─────────────┼───────────┤
│ 6161138431505 │ Michael     │ Kane      │
│ 1867355902434 │ Jordan      │ Jarvis    │
│ 5655135874036 │ Arthur      │ Haley     │
│ 8004712047366 │ Kim         │ Welch     │
│       ·       │   ·         │   ·       │
│       ·       │   ·         │   ·       │
│       ·       │   ·         │   ·       │
│ 7479524472455 │ Justin      │ Carey     │
│ 1347469827969 │ Randy       │ Rosario   │
│ 7555403134688 │ Jessica     │ Morris    │
├───────────────┴─────────────┴───────────┤
│ 100000 rows (40 shown)        3 columns │
└─────────────────────────────────────────┘
```

Now we’re ready to load our parquet files into DuckDB. You can also do this in one line in the shell.

```plaintext
Copy code

echo "CREATE TABLE persons AS SELECT * FROM 'outfile_*.parquet'" | duckdb ./people.ddb
```

At the time that I ran this query, I had 10M rows in the parquet files and it loaded in 2.8 seconds.

## Easy Parallelization using GNU Parallel

I’m a big fan of using shell utilities – everything from sed and grep to my all-time favorite [ParallelSSH](https://parallel-ssh.org/), which I used almost 20 years ago to maintain a fleet of machines. In this case though (as long as we have fast enough machines, including I/O), we don’t need parallel execution across many machines, but can use [GNU Parallel](https://www.gnu.org/software/parallel/) to execute the same python code many times in parallel.

The following code will execute `generator.py` 10 times, resulting in parquet files with a total of 1M person records, sharded into 10 different files. It takes only 33 seconds on the wall clock to execute on a 10 core machine.

```plaintext
Copy code

# pass numbers 1 to 10 on separate lines to GNU parallel
seq 10 | time parallel python generate.py
parallel python generate.py  307.06s user 5.72s system 938% cpu 33.313 total
```

Note that this will result in calling:

```plaintext
Copy code

python generate.py 1
python generate.py 2
…
python generate.py 10
```

I tried increasing the `seq 10` to `seq 100` and it scaled linearly. By default, GNU Parallel only runs 1 job in parallel for each CPU core. If you suspect that it’ll work faster for your use case, you can actually launch more than 1 job per core and let the scheduler optimize. Here’s how you launch 2 jobs for every core:

```plaintext
Copy code

seq 100 | time parallel -j 200% python genera.py
```

For this particular job, it actually takes slightly longer to do this as, from the looks of top and the size of the generated files, we’re maxing out the CPU core for each python process.

## Generating 1 Billion People

I used the GNU Parallel technique discussed above with a hefty m6i.32xlarge instance on Amazon EC2, though generated a billion people in 1k parquet files. This took about 2 hours to generate. After generation, executing a full table scan query (`SELECT  SUM(id) FROM '*.parquet' WHERE email LIKE '%gmail.com'`) took only 6 seconds.

I then into the data into DuckDB's native storage, producing a 36GB DuckDB file in about 2 minutes. My first full table scan query took 10.82 seconds, but subsequent queries (with different values, no caching) took only 1.03 seconds. Whoa!

## Next Steps

In this example, we only generated fake records for person objects. In my code, I actually generated a person, along with a corresponding bank account and address. I then generated a random number of additional accounts and addresses for each person. These were populated into different tables in DuckDB, related to each other by the ID generated for a person.

My code initially used a CSV format for testing loading performance of CSVs. In other scenarios, I’d likely choose generating parquet files as they’re much more efficient on disk.

```python
Copy code

# generate 1.5B people and 1.5B+ addresses and accounts
records = 1500000000

print("Generating %s random people records" % records)

for y in range(records):
  (person, address, bacct) = get_fake_data()
  pwriter.writerow(person)
  awriter.writerow(address)
  bwriter.writerow(bacct)

  for x in range(random.randrange(0, 2)):
    address = get_fake_address(person['id'])
    awriter.writerow(address)

  for x in range(random.randrange(0, 3)):
    bacct = get_fake_account(person['id'])
    bwriter.writerow(bacct)
```

What generated data will you make using Faker? Let us know on twitter via [@motherduck](https://twitter.com/motherduck).

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: January 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFrame_8538_1_19a9e51746.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-two/)

[2023/01/12 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-two/)

### [This Month in the DuckDB Ecosystem: January 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-two)

DuckDB community member Marcos Ortiz shares his favorite links and upcoming events across the community. Includes featured community member Jacob Matson who wrote about the Modern Data Stack in a Box with DuckDB.

[![How to analyze SQLite databases in DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_sqlite_ae3ed17fef.png&w=3840&q=75)](https://motherduck.com/blog/analyze-sqlite-databases-duckdb/)

[2023/01/24 - Ryan Boyd](https://motherduck.com/blog/analyze-sqlite-databases-duckdb/)

### [How to analyze SQLite databases in DuckDB](https://motherduck.com/blog/analyze-sqlite-databases-duckdb)

DuckDB is often referred to as the SQLite for analytics. This blog post talks about how to query SQLite transactional databases from within the DuckDB analytics database.

[View all](https://motherduck.com/blog/)

Twitter Widget Iframe

Authorization Response