import requests
import random
import logging
import argparse

from bs4 import BeautifulSoup


def fetch_afisha_page():
    logging.info('Obtaining the list of movies from afisha...')
    afisha_url = 'http://www.afisha.ru/msk/schedule_cinema/'
    return requests.get(afisha_url).text


def parse_afisha_list(raw_html):
    soup = BeautifulSoup(raw_html, 'lxml')

    movies_titles_tags = soup.find_all('div', {'class': 'm-disp-table'})

    movies_titles_and_cinemas_count = {}
    for movie_title_tag in movies_titles_tags:
        movie_title = movie_title_tag.find('a').text
        cinemas_count = len(movie_title_tag.parent.find_all('td', {'class': 'b-td-item'}))
        movies_titles_and_cinemas_count[movie_title] = cinemas_count

    return movies_titles_and_cinemas_count


def fetch_kinopoisk_movie_page(movie_title, proxy_list):
    timeout = 3
    kinopoisk_page_url = 'https://www.kinopoisk.ru/index.php'
    params = {
        'kp_query': movie_title,
        'first': 'yes'
    }

    while True:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Agent:%s'.format(get_random_agent())
        }
        proxy_ip = get_random_proxy(proxy_list)
        proxy = {'http': proxy_ip}

        logging.info('Try proxy %s...', proxy_ip)

        try:
            request = requests.Session().get(
                kinopoisk_page_url,
                params=params,
                headers=headers,
                proxies=proxy,
                timeout=timeout
            )
        except(requests.exceptions.ConnectTimeout,
               requests.exceptions.ConnectionError,
               requests.exceptions.ProxyError,
               requests.exceptions.ReadTimeout):
            logging.exception('Connect error. Reconnect...')
        else:
            break

    return request.text


def parse_kinopoisk_movie_page(raw_html):
    try:
        soup = BeautifulSoup(raw_html, 'lxml')
        rating = soup.find('span', {'class': 'rating_ball'}).text
        rating_count = soup.find('span', {'class': 'ratingCount'}).text
    except AttributeError:
        rating = rating_count = None
    return rating, rating_count


def get_movies_info():
    afisha_page = fetch_afisha_page()
    movies_titles_and_cinemas_count = parse_afisha_list(afisha_page)

    proxies_list = get_proxies_list()

    movies_count = len(movies_titles_and_cinemas_count.keys())
    movies_info = {}
    for num, movie in enumerate(movies_titles_and_cinemas_count.keys()):
        logging.info('[%d/%d] Get "%s" page...', num + 1, movies_count, movie)
        kinopoisk_page = fetch_kinopoisk_movie_page(movie, proxies_list)
        rating, rating_count = parse_kinopoisk_movie_page(kinopoisk_page)
        movies_info[movie] = {
            'cinemas_count': movies_titles_and_cinemas_count[movie],
            'rating': rating,
            'rating_count': rating_count
        }
    return movies_info


def sort_movies_list(movies):
    return sorted(
        movies.items(),
        key=lambda item: item[1]['rating'] if item[1]['rating'] is not None else '0',
        reverse=True
    )


def output_movies_to_console(movies, movies_count, cinemas_count_limit):
    logging.info('Movies with the greatest rating (cinemas count >= %d):', cinemas_count_limit)
    movies_with_cinemas_count_limit = [movie for movie in movies if movie[1]['cinemas_count'] >= cinemas_count_limit]
    for num, movie in enumerate(movies_with_cinemas_count_limit[:movies_count]):
        print(
            '{0} "{1}" (RATING: {2}; RATING COUNT: {3}; CINEMAS COUNT: {4})'.format(
                num + 1,
                movie[0],
                movie[1]['rating'],
                movie[1]['rating_count'],
                movie[1]['cinemas_count'],
            )
        )


def get_random_agent():
    agent_list = [
        'Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0',
        'Opera/9.80 (Windows NT 6.2; WOW64) Presto/2.12.388 Version/12.17',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0'
    ]
    return random.choice(agent_list)


def get_proxies_list():
    proxy_url = 'http://www.freeproxy-list.ru/api/proxy'
    params = {'anonymity': 'true', 'token': 'demo'}
    request = requests.get(proxy_url, params=params).text
    proxies_list = request.split('\n')
    return proxies_list


def get_random_proxy(proxy_list):
    return random.choice(proxy_list)


def get_args():
    parser = argparse.ArgumentParser(description='Script for obtaining movies list with the greatest rating')
    parser.add_argument(
        '--movies_count',
        type=int,
        default=10,
        help='Movies count for console output (10 by default)')
    parser.add_argument(
        '--cinemas_count_limit',
        type=int,
        default=1,
        help='The lower bound for the cinemas count (1 by default)')
    return parser.parse_args()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s# %(levelname)-8s [%(asctime)s] %(message)s',
        datefmt=u'%m/%d/%Y %I:%M:%S %p'
    )

    args = get_args()

    movies_info = get_movies_info()
    sorted_movies = sort_movies_list(movies_info)
    output_movies_to_console(sorted_movies, args.movies_count, args.cinemas_count_limit)
