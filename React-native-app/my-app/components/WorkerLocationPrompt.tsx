import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import apiService from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

// Shown on the worker dashboard until the worker has saved a location.
// Clients choosing "nearest worker" can only be matched with workers who
// have one, and no worker had set it from the profile screen.
export default function WorkerLocationPrompt() {
  const { theme } = useTheme();
  const [visible, setVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    apiService.getWorkerProfile()
      .then((profile: any) => setVisible(profile?.latitude == null || profile?.longitude == null))
      .catch(() => setVisible(false));
  }, []);

  const saveLocation = async () => {
    setSaving(true);
    setMessage('');
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setMessage('Please allow location access to be matched with clients near you.');
        return;
      }
      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      await apiService.updateWorkerProfile({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      });
      setVisible(false);
    } catch (error) {
      setMessage('Could not save your location. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!visible) return null;

  return (
    <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.primary }]}>
      <View style={styles.row}>
        <Ionicons name="location" size={22} color={theme.primary} />
        <View style={styles.textBox}>
          <Text style={[styles.title, { color: theme.text }]}>Get jobs near you</Text>
          <Text style={[styles.body, { color: theme.textSecondary }]}>
            Save your location so clients nearby can be matched with you automatically. Tap the button where you usually work.
          </Text>
        </View>
      </View>
      {message ? <Text style={[styles.message, { color: theme.textSecondary }]}>{message}</Text> : null}
      <TouchableOpacity
        style={[styles.button, { backgroundColor: theme.primary }]}
        onPress={saveLocation}
        disabled={saving}
      >
        {saving ? (
          <ActivityIndicator size="small" color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Save my location</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 14, padding: 14, marginBottom: 16 },
  row: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  textBox: { flex: 1 },
  title: { fontSize: 15, fontWeight: '700', marginBottom: 2 },
  body: { fontSize: 13, lineHeight: 18 },
  message: { fontSize: 12, marginTop: 8 },
  button: { marginTop: 12, borderRadius: 10, paddingVertical: 10, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
