<template>
  <div class="not-found">
    <span class="code">404</span>
    <h1>Page introuvable</h1>
    <p>Cette page n'existe pas ou a été déplacée.</p>
    <RouterLink to="/" class="btn-home">Retour à l'accueil</RouterLink>
  </div>
</template>

<style scoped>
.not-found {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 60vh; text-align: center; gap: var(--s-4);
}
.code {
  font-size: 6rem; font-weight: var(--fw-bold); color: var(--accent); opacity: 0.2; line-height: 1;
}
h1 { font-size: var(--t-2xl); color: var(--fg); margin: 0; }
p  { color: var(--fg-dim); margin: 0; }
.btn-home {
  margin-top: var(--s-2); background: var(--accent); color: #fff;
  padding: 10px 24px; border-radius: var(--r-md); text-decoration: none;
  font-weight: var(--fw-semibold); font-size: var(--t-base);
}
</style>
