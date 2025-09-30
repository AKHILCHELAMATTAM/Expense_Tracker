from django.db import models
from django.db.models import Q
from django.utils import timezone

class AppUser(models.Model):
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='expenses', db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='expenses', db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    spent_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'spent_at']),
            models.Index(fields=['category']),
        ]
        constraints = [
            models.CheckConstraint(check=Q(amount__gte=0), name='expense_amount_non_negative'),
        ]

    def __str__(self):
        return f'{self.user} - {self.category} - {self.amount}'