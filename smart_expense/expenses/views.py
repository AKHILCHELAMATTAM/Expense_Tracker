from decimal import Decimal
from django.db import connection
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AppUser, Category, Expense
from .serializers import (
    AppUserSerializer, CategorySerializer,
    ExpenseCreateSerializer, ExpenseOutSerializer
)

# Users: GET/POST /api/users
@api_view(['GET', 'POST'])
def users_view(request):
    if request.method == 'POST':
        serializer = AppUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = AppUser.objects.create(**serializer.validated_data)
            except Exception:
                return Response({'detail': 'User with that name/email may already exist.'},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(AppUserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    users = AppUser.objects.order_by('id')
    return Response(AppUserSerializer(users, many=True).data)

# Categories: GET/POST /api/categories
@api_view(['GET', 'POST'])
def categories_view(request):
    if request.method == 'POST':
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            try:
                cat = Category.objects.create(**serializer.validated_data)
            except Exception:
                return Response({'detail': 'Category may already exist.'},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(CategorySerializer(cat).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    cats = Category.objects.order_by('name')
    return Response(CategorySerializer(cats, many=True).data)

# Expenses: GET /api/expenses?user_id=... and POST /api/expenses
@api_view(['GET', 'POST'])
def expenses_view(request):
    if request.method == 'POST':
        serializer = ExpenseCreateSerializer(data=request.data)
        if serializer.is_valid():
            exp = serializer.save()
            out = ExpenseOutSerializer(exp)
            return Response(out.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    qs = Expense.objects.select_related('category').filter(user_id=user_id).order_by('-spent_at', '-id')
    data = ExpenseOutSerializer(qs, many=True).data
    return Response(data)

# Monthly Summary: GET /api/reports/monthly_summary?year=YYYY&month=MM&user_id=<id>
@api_view(['GET'])
def monthly_summary_view(request):
    try:
        year = int(request.query_params.get('year'))
        month = int(request.query_params.get('month'))
        user_id = int(request.query_params.get('user_id'))
    except (TypeError, ValueError):
        return Response({'detail': 'year, month, and user_id are required integers.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not (1 <= month <= 12):
        return Response({'detail': 'month must be 1-12.'}, status=status.HTTP_400_BAD_REQUEST)

    month_str = f'{month:02d}'
    year_str = f'{year:04d}'

    vendor = connection.vendor  # 'sqlite' | 'postgresql' | 'mysql' etc.
    if vendor == 'sqlite':
        year_cond = "strftime('%%Y', e.spent_at) = %s"
        month_cond = "strftime('%%m', e.spent_at) = %s"
        params = [user_id, year_str, month_str]
    elif vendor == 'postgresql':
        year_cond = "EXTRACT(YEAR FROM e.spent_at) = %s"
        month_cond = "EXTRACT(MONTH FROM e.spent_at) = %s"
        params = [user_id, year, month]
    else:
        # Generic ANSI-ish fallback using year/month extraction if supported
        year_cond = "EXTRACT(YEAR FROM e.spent_at) = %s"
        month_cond = "EXTRACT(MONTH FROM e.spent_at) = %s"
        params = [user_id, year, month]

    sql = f"""
        WITH filtered AS (
            SELECT e.amount, e.category_id
            FROM expenses_expense e
            WHERE e.user_id = %s
              AND {year_cond}
              AND {month_cond}
        ),
        agg AS (
            SELECT c.name AS category_name, SUM(f.amount) AS total_amount
            FROM filtered f
            JOIN expenses_category c ON c.id = f.category_id
            GROUP BY c.name
        ),
        total AS (
            SELECT COALESCE(SUM(amount), 0) AS total_expenses FROM filtered
        )
        SELECT
            (SELECT total_expenses FROM total) AS total_expenses,
            a.category_name AS category_name,
            a.total_amount AS total_amount
        FROM agg a
        ORDER BY a.category_name ASC
    """

    with connection.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        return JsonResponse({'total_expenses': '0.00', 'expenses_by_category': []})

    # total_expenses is duplicated per row; take from first row
    from decimal import ROUND_HALF_UP
    total = Decimal(rows[0][0] or 0).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    by_cat = []
    for _, name, amt in rows:
        amt = Decimal(amt or 0).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        by_cat.append({'category_name': name, 'total_amount': f'{amt}'})

    return JsonResponse({'total_expenses': f'{total}', 'expenses_by_category': by_cat})