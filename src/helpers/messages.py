import re
import logging

def extract_link(text):
    match = re.search(r'(https?://\S+)', text)
    return match.group(1) if match else None

def parse_rating(text):
    rating, explanation = None, None
    try:
        lines = text.split('\n')
        reviewI = None
        for i, line in enumerate(lines):
            parts = line.split('-')
            if len(parts) > 1 and parts[-1].strip().isdigit():
                rating = parts[-1].strip()
                reviewI = i + 1
                break
        if reviewI is not None and reviewI < len(lines):
            explanation = '\n'.join(lines[reviewI:]).strip()
    except Exception as e:
        logging.error(f'Error parsing rating: {e}')
        rating, explanation = None, None
    return rating, explanation


def parse_recommendation(text):
    try:
        lines = text.split('\n')
        parts = lines[0].split('-')
        tag = parts[-1].strip()
        genre = "-".join(parts[0:-1]).strip()
    except Exception as e:
        logging.error(f'Error parsing recommendation: {e}')
        genre, tag = None, None
    return genre, tag


def parse_embed(embed):
    try:
        title = embed.title if embed.title else ''
        author = embed.author.name if embed.author else ''
        author = author.rstrip(' - Topic')
        link = embed.url if hasattr(embed, 'url') else None
    except Exception as e:
        logging.error(f'Error parsing embed: {e}')
        title, author, link = None, None, None
    return title, author, link
    
