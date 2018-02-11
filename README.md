# Social Mind

## A new network for mental health

###Business Understanding

Finding the right combination of treatment and support
for mental health issues can be a long, expensive, and unfulfilling process.
The most commonly reported reason for people being unable to obtain
the mental health services they need is cost, which leads many to seek
cheaper alternatives or supplement their therapy with outside social support.
However, these resources are also limited by time, location, and lack of funding.
This tool utilizes natural language processing to match people with others who
share a unique manifestation of a disorder and demonstrates the potential of
this technology to enhance the therapeutic process.

###Data Understanding

I used the only data currently accessible - public mental health forums. There
are some drawbacks and advantages to using data from this domain. Data on mental forums
are typically in the form of post and response. Responses generally address other
people rather than the person writing, and so had to be filtered out for the
purposes of this project. However, this provides a nice foundation for capturing
only patient dialogue if this tool were to be utilized in a therapeutic setting.

###Data Preparation

The scope of this project focused on anxiety as it is the most common disorder
in the United States, has a high lifetime prevalence, and presents with a lot of variation
both in symptoms and environmental triggers.

Two public mental health forums
with anonymous posts were webscraped using BeautifulSoup.

A Naive Bayes model was used to filter out posts that were only mental health
related and personal. This was to ensure i was matching users who shared similar
expressions of anxiety.

Posts with less than 10 words were also filtered as most of them were either not
personal or provided very little meaning about a person's experience and symptomology.
Posts were atomized, filtered for punctuation, and lemmatized before modeling.  

###Modeling

A Natural Language Processing model was used to match similar posts using
cosine similarity. My data could be categorized into 3 broad categories:

1) generalized anxiety
2) social anxiety
3) panic and phobias

I validated my model by going to a new forum that i hadn't scraped that also
had these subcategories. I pulled 2 posts within each and used these as queries in
my model to see how well it generated similar posts.

An n-grams model with a range up to 2 worked a bit better than n-grams of 1 by
capturing more of the connection between feelings and behaviors. Shorter posts
tended to be matched more because its normalizing vector was inherently smaller.
I chose to penalize shorter posts by creating a weight that ensured a minimum number
of similar features. I chose a function with a decreasing rate to allow for the fact
that words tend to be repeated with longer posts. This worked better for
some queries and worse for others.

Graph Theory was also used to demonstrate how comparing posts within a user
could be used to enhance therapy, especially therapies centered on identifying
thought patterns and environmental triggers, like cognitive behavioral therapy.

###Deployment

This project is ongoing with the eventual goal being implementation. A webapp
demo was created to visually demonstrate the value of matching users. Further work
includes different modeling techniques, research, and testing.  
