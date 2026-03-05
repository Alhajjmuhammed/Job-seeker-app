import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../contexts/ThemeContext';

interface StarRatingProps {
  rating: number;
  onRatingChange?: (rating: number) => void;
  size?: number;
  readonly?: boolean;
  showLabel?: boolean;
}

export default function StarRating({
  rating,
  onRatingChange,
  size = 32,
  readonly = false,
  showLabel = true,
}: StarRatingProps) {
  const { theme } = useTheme();
  const [tempRating, setTempRating] = useState(0);

  const handlePress = (value: number) => {
    if (!readonly && onRatingChange) {
      onRatingChange(value);
    }
  };

  const handlePressIn = (value: number) => {
    if (!readonly) {
      setTempRating(value);
    }
  };

  const handlePressOut = () => {
    setTempRating(0);
  };

  const displayRating = tempRating || rating;

  const getRatingLabel = (rating: number) => {
    if (rating === 0) return 'Tap to rate';
    if (rating === 1) return 'Poor';
    if (rating === 2) return 'Fair';
    if (rating === 3) return 'Good';
    if (rating === 4) return 'Very Good';
    if (rating === 5) return 'Excellent';
    return '';
  };

  return (
    <View style={styles.container}>
      <View style={styles.starsContainer}>
        {[1, 2, 3, 4, 5].map((value) => (
          <TouchableOpacity
            key={value}
            onPress={() => handlePress(value)}
            onPressIn={() => handlePressIn(value)}
            onPressOut={handlePressOut}
            disabled={readonly}
            activeOpacity={0.7}
            style={styles.starButton}
          >
            <Ionicons
              name={value <= displayRating ? 'star' : 'star-outline'}
              size={size}
              color={value <= displayRating ? '#FFD700' : theme.textTertiary}
            />
          </TouchableOpacity>
        ))}
      </View>
      {showLabel && (
        <Text style={[styles.ratingLabel, { color: theme.textSecondary }]}>
          {getRatingLabel(displayRating)}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  starsContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  starButton: {
    padding: 4,
  },
  ratingLabel: {
    marginTop: 8,
    fontSize: 16,
    fontWeight: '600',
  },
});
