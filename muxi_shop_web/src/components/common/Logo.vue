<template>
  <div class="logo-wrapper">
    <router-link to="/">
      <img class="logo" src="@/assets/images/logo/logo-big.png" alt="木犀商城" />
    </router-link>
  </div>
</template>

<style scoped lang="less">
.logo-wrapper {
  width: 200px;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  .logo {
    width: 100px;
    height: 100px;
  }
}
</style>
