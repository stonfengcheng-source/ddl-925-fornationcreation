import options from '../../../configs/module4/evaluation_options.json';

export const evaluationSubjects = options.subjects;
export const evaluationProfiles = options.profiles;
export const evaluationModeOptions = [
  ...evaluationProfiles.map(profile => ({
    value: profile.value,
    label: `${profile.label} · ${profile.subjects.length} 科目，${profile.samples_per_subject === null ? '全部题目' : `每科最多 ${profile.samples_per_subject} 题（共最多 ${profile.subjects.length * profile.samples_per_subject} 题）`}`,
  })),
  { value: 'custom', label: '自定义 · 自选科目与题量' },
];

export function evaluationPreset(mode: string) {
  const profile = evaluationProfiles.find(profile => profile.value === mode);
  return profile ? {
    eval_subjects: [...profile.subjects],
    eval_samples_per_subject: profile.samples_per_subject ?? 10,
    eval_all_questions: profile.samples_per_subject === null,
  } : undefined;
}
