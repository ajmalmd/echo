from django.core.paginator import Paginator

def paginate_items(request, items, per_page=10):
    """
    This function takes the request, a list of items (like products),
    and the number of items per page (default is 10), and returns the
    page object for pagination.

    :param request: HttpRequest object
    :param items: Iterable (list, QuerySet, etc.)
    :param per_page: Number of items per page
    :return: page_obj for pagination
    """
    page_number = request.GET.get('page', 1)  # Default to first page if no 'page' param is provided
    page_number = int(page_number)  # Ensure it's an integer
    
    paginator = Paginator(items, per_page)  # Paginate the items
    page_obj = paginator.get_page(page_number)  # Get the page object for the current page
    
    return page_obj