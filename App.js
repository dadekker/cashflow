import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Linking,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'gym_logs_v1';

const DAYS = [
  {
    id: 'mon',
    name: 'Mon',
    title: 'Upper Push',
    duration: '60 min',
    exercises: [
      { name: 'Flat barbell bench', sets: '4×6–8', youtube: 'https://www.youtube.com/results?search_query=flat+barbell+bench+press+form' },
      { name: 'Incline dumbbell press', sets: '3×8–10', youtube: 'https://www.youtube.com/results?search_query=incline+dumbbell+press+form' },
      { name: 'Weighted dips or machine chest press', sets: '3×10–12', youtube: 'https://www.youtube.com/results?search_query=weighted+dips+or+machine+chest+press+form' },
      { name: 'Standing overhead press', sets: '3×6–8', youtube: 'https://www.youtube.com/results?search_query=standing+overhead+press+form' },
      { name: 'Lateral raises', sets: '4×12–15', youtube: 'https://www.youtube.com/results?search_query=lateral+raises+form' },
      { name: 'Cable triceps pushdown', sets: '3×12', youtube: 'https://www.youtube.com/results?search_query=cable+triceps+pushdown+form' },
      { name: 'Overhead triceps extension', sets: '3×12', youtube: 'https://www.youtube.com/results?search_query=overhead+triceps+extension+form' },
    ],
  },
  {
    id: 'tue', name: 'Tue', title: 'Lower (hamstring-safe)', duration: '50 min',
    exercises: [
      { name: 'Goblet or front squat', sets: '4×6–8', youtube: 'https://www.youtube.com/results?search_query=goblet+squat+or+front+squat+form' },
      { name: 'Leg press', sets: '3×10–12', youtube: 'https://www.youtube.com/results?search_query=leg+press+form' },
      { name: 'Bulgarian split squat', sets: '3×8 each leg', youtube: 'https://www.youtube.com/results?search_query=bulgarian+split+squat+form' },
      { name: 'Walking lunges', sets: '3×10', youtube: 'https://www.youtube.com/results?search_query=walking+lunges+form' },
      { name: 'Standing calf raise', sets: '4×12', youtube: 'https://www.youtube.com/results?search_query=standing+calf+raise+form' },
      { name: 'Hanging leg raise', sets: '3×12', youtube: 'https://www.youtube.com/results?search_query=hanging+leg+raise+form' },
      { name: 'Cable crunch', sets: '3×15', youtube: 'https://www.youtube.com/results?search_query=cable+crunch+form' },
    ],
    notes: 'Skip stiff-legged deadlifts and Nordic curls until hamstring is consistently pain-free. Add hip thrusts 3×10 once it feels bulletproof.',
  },
  {
    id: 'wed', name: 'Wed', title: 'Upper Pull', duration: '60 min',
    exercises: [
      { name: 'Weighted pull-ups', sets: '4×6–8', youtube: 'https://www.youtube.com/results?search_query=weighted+pull+ups+form' },
      { name: 'Chest-supported row', sets: '3×8–10', youtube: 'https://www.youtube.com/results?search_query=chest+supported+row+form' },
      { name: 'Lat pulldown', sets: '3×10–12', youtube: 'https://www.youtube.com/results?search_query=lat+pulldown+form' },
      { name: 'Cable row', sets: '3×10', youtube: 'https://www.youtube.com/results?search_query=cable+row+form' },
      { name: 'Face pulls', sets: '3×15', youtube: 'https://www.youtube.com/results?search_query=face+pull+form' },
      { name: 'Barbell or EZ-bar curl', sets: '3×8–10', youtube: 'https://www.youtube.com/results?search_query=ez+bar+curl+form' },
      { name: 'Hammer curl', sets: '3×10', youtube: 'https://www.youtube.com/results?search_query=hammer+curl+form' },
      { name: 'Rear delt fly', sets: '3×15', youtube: 'https://www.youtube.com/results?search_query=rear+delt+fly+form' },
    ],
  },
  {
    id: 'thu', name: 'Thu', title: 'Cycle commute + Zone 2', duration: '30+ min',
    exercises: [
      { name: 'Bike commute (Zone 2)', sets: 'steady effort', youtube: 'https://www.youtube.com/results?search_query=zone+2+cycling+how+to' },
      { name: 'Optional longer ride or incline walk', sets: '20–40 min', youtube: 'https://www.youtube.com/results?search_query=zone+2+incline+walking' },
    ],
  },
  {
    id: 'fri', name: 'Fri', title: 'Upper (chest & shoulder focus)', duration: '60 min',
    exercises: [
      { name: 'Incline barbell bench', sets: '4×6–8', youtube: 'https://www.youtube.com/results?search_query=incline+barbell+bench+press+form' },
      { name: 'Flat dumbbell press', sets: '3×8–10', youtube: 'https://www.youtube.com/results?search_query=flat+dumbbell+press+form' },
      { name: 'Cable fly (high-to-low and low-to-high)', sets: '4×12', youtube: 'https://www.youtube.com/results?search_query=cable+fly+high+to+low+low+to+high+form' },
      { name: 'Seated dumbbell shoulder press', sets: '3×8', youtube: 'https://www.youtube.com/results?search_query=seated+dumbbell+shoulder+press+form' },
      { name: 'Cable lateral raise', sets: '4×15', youtube: 'https://www.youtube.com/results?search_query=cable+lateral+raise+form' },
      { name: 'Close-grip bench', sets: '3×8', youtube: 'https://www.youtube.com/results?search_query=close+grip+bench+press+form' },
      { name: 'Incline dumbbell curl', sets: '3×10', youtube: 'https://www.youtube.com/results?search_query=incline+dumbbell+curl+form' },
    ],
  },
  {
    id: 'sat', name: 'Sat', title: 'Lower + core', duration: '50 min',
    exercises: [
      { name: 'Trap-bar deadlift (light, controlled)', sets: '4×5', youtube: 'https://www.youtube.com/results?search_query=trap+bar+deadlift+form' },
      { name: 'Hack squat or leg press', sets: '3×10', youtube: 'https://www.youtube.com/results?search_query=hack+squat+or+leg+press+form' },
      { name: 'Leg extension', sets: '3×12', youtube: 'https://www.youtube.com/results?search_query=leg+extension+form' },
      { name: 'Hip thrust', sets: '3×10', youtube: 'https://www.youtube.com/results?search_query=hip+thrust+form' },
      { name: 'Standing calf', sets: '4×12', youtube: 'https://www.youtube.com/results?search_query=standing+calf+raise+form' },
      { name: 'Ab wheel rollout', sets: '3×10', youtube: 'https://www.youtube.com/results?search_query=ab+wheel+rollout+form' },
      { name: 'Decline weighted sit-up', sets: '3×12', youtube: 'https://www.youtube.com/results?search_query=decline+weighted+sit+up+form' },
      { name: 'Plank', sets: '3×45s', youtube: 'https://www.youtube.com/results?search_query=proper+plank+form' },
    ],
  },
];

export default function App() {
  const currentDayIdx = Math.min(new Date().getDay() - 1, 5);
  const [selectedDay, setSelectedDay] = useState(currentDayIdx >= 0 ? currentDayIdx : 0);
  const [logs, setLogs] = useState({});

  useEffect(() => {
    (async () => {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw) setLogs(JSON.parse(raw));
    })();
  }, []);

  const day = DAYS[selectedDay];

  const saveLogs = async (next) => {
    setLogs(next);
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const saveWeight = async (exerciseName, weight) => {
    const today = new Date().toISOString().slice(0, 10);
    const key = `${day.id}::${exerciseName}`;
    const next = { ...logs };
    next[key] = [...(next[key] || []), { date: today, weight: Number(weight) }];
    await saveLogs(next);
    Alert.alert('Saved', `${exerciseName}: ${weight} logged on ${today}`);
  };

  const progress = useMemo(() => {
    const map = {};
    Object.entries(logs).forEach(([k, arr]) => {
      map[k] = [...arr].sort((a, b) => a.date.localeCompare(b.date));
    });
    return map;
  }, [logs]);

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.header}>Gym Schedule Tracker</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.dayTabs}>
        {DAYS.map((d, idx) => (
          <TouchableOpacity key={d.id} style={[styles.tab, selectedDay === idx && styles.tabActive]} onPress={() => setSelectedDay(idx)}>
            <Text style={styles.tabText}>{d.name}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView style={styles.content}>
        <Text style={styles.title}>{day.title} ({day.duration})</Text>
        {day.notes ? <Text style={styles.note}>{day.notes}</Text> : null}

        {day.exercises.map((ex) => (
          <ExerciseCard key={ex.name} ex={ex} dayId={day.id} onSave={saveWeight} progress={progress[`${day.id}::${ex.name}`] || []} />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function ExerciseCard({ ex, onSave, progress }) {
  const [weight, setWeight] = useState('');

  return (
    <View style={styles.card}>
      <Text style={styles.exercise}>{ex.name}</Text>
      <Text style={styles.sets}>{ex.sets}</Text>
      <TouchableOpacity onPress={() => Linking.openURL(ex.youtube)}>
        <Text style={styles.link}>Open technique video</Text>
      </TouchableOpacity>
      <View style={styles.row}>
        <TextInput
          value={weight}
          onChangeText={setWeight}
          placeholder="Weight used"
          keyboardType="numeric"
          style={styles.input}
        />
        <TouchableOpacity
          style={styles.saveBtn}
          onPress={() => {
            if (!weight) return;
            onSave(ex.name, weight);
            setWeight('');
          }}
        >
          <Text style={styles.saveText}>Log</Text>
        </TouchableOpacity>
      </View>
      {progress.length > 0 ? (
        <View>
          <Text style={styles.progressHeader}>Recent:</Text>
          {progress.slice(-5).reverse().map((p, idx) => (
            <Text key={`${p.date}-${idx}`} style={styles.progressLine}>{p.date}: {p.weight}</Text>
          ))}
        </View>
      ) : (
        <Text style={styles.progressLine}>No logs yet</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f4f4', paddingTop: 12 },
  header: { fontSize: 26, fontWeight: '700', textAlign: 'center', marginBottom: 12 },
  dayTabs: { maxHeight: 48, paddingHorizontal: 8 },
  tab: { backgroundColor: '#ddd', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, marginRight: 8 },
  tabActive: { backgroundColor: '#1f6feb' },
  tabText: { color: '#111', fontWeight: '600' },
  content: { paddingHorizontal: 12 },
  title: { fontSize: 20, fontWeight: '700', marginVertical: 10 },
  note: { backgroundColor: '#fff2c4', padding: 10, borderRadius: 8, marginBottom: 10 },
  card: { backgroundColor: 'white', borderRadius: 12, padding: 12, marginBottom: 10 },
  exercise: { fontSize: 16, fontWeight: '700' },
  sets: { color: '#666', marginBottom: 6 },
  link: { color: '#1f6feb', marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center' },
  input: { flex: 1, backgroundColor: '#f6f6f6', borderRadius: 8, padding: 10, marginRight: 8 },
  saveBtn: { backgroundColor: '#1f6feb', paddingVertical: 10, paddingHorizontal: 14, borderRadius: 8 },
  saveText: { color: 'white', fontWeight: '700' },
  progressHeader: { marginTop: 8, fontWeight: '700' },
  progressLine: { color: '#444', marginTop: 2 },
});
