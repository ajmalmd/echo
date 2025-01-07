def wishlist_context(request):
    """
    Adds the user's wishlist to the template context.
    """
    if request.user.is_authenticated:
        # Replace 'wishlist' with the actual related name in your model
        wishlist = request.user.wishlist.values_list("product_variant", flat=True)
    else:
        wishlist = []
    return {"wishlist": wishlist}