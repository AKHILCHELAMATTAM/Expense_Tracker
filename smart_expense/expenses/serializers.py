from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from .models import AppUser, Category, Expense

def money_str(d: Decimal) -> str:
    return str((d or Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class AppUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ['id', 'name', 'email']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ExpenseCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(allow_blank=True, required=False)
    spent_at = serializers.DateTimeField(required=False)

    def create(self, validated_data):
        from .models import AppUser, Category, Expense
        try:
            user = AppUser.objects.get(id=validated_data['user_id'])
        except AppUser.DoesNotExist:
            raise serializers.ValidationError({'user_id': 'User not found.'})
        try:
            category = Category.objects.get(id=validated_data['category_id'])
        except Category.DoesNotExist:
            raise serializers.ValidationError({'category_id': 'Category not found.'})

        return Expense.objects.create(
            user=user,
            category=category,
            amount=validated_data['amount'],
            description=validated_data.get('description') or None,
            spent_at=validated_data.get('spent_at'),
        )

class ExpenseOutSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = ['id', 'user_id', 'category_id', 'category_name', 'amount', 'description', 'spent_at']

    def get_amount(self, obj):
        return money_str(obj.amount)